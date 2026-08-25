# Nginx 배포

## 요청 흐름

```text
브라우저: http://localhost:8010
  -> Nginx 컨테이너: 8010 -> 80
    -> FastAPI 컨테이너: 8000
      -> 기존 PostgreSQL 컨테이너: dasi-space-postgres:5432
```

Nginx만 호스트의 `8010` 포트를 공개합니다. FastAPI와 PostgreSQL은 Docker 네트워크 안에서 통신하며, 기존 `7_default` 네트워크와 PostgreSQL 볼륨은 다시 만들거나 삭제하지 않습니다.

## 사전 조건

- Docker Desktop이 실행 중이어야 합니다.
- `dasi-space-postgres` 컨테이너가 `7_default` 네트워크에서 실행 중이어야 합니다.
- `project/.env`에 `KAKAO_MAP_APP_KEY`와 운영용 `JWT_SECRET`이 설정되어 있어야 합니다.
- Kakao Developers의 JavaScript SDK 허용 도메인에 `http://localhost:8010`이 등록되어 있어야 합니다.

## No-IP 공개 호스트명

No-IP에서 호스트명을 만든 뒤 DDNS를 활성화하고 DDNS Key를 생성합니다. 계정 비밀번호 대신 호스트별 DDNS Key를 사용하며, 비밀번호는 저장소나 메신저에 공유하지 않습니다.

Windows용 No-IP DUC에 DDNS Key로 로그인해 호스트를 선택하거나, 공유기가 No-IP DDNS를 지원하면 공유기에서 갱신을 설정합니다. 같은 호스트를 DUC와 공유기 양쪽에서 동시에 갱신하지 않습니다.

`.env.example`을 참고해 `project/.env`에 다음 값을 추가합니다.

```dotenv
PUBLIC_HOST=your-hostname.ddns.net
PUBLIC_ORIGIN=http://your-hostname.ddns.net
HTTP_PORT=8010
HTTPS_PORT=8443
NGINX_CONFIG=./deploy/nginx-http.conf.template
```

공유기에서는 외부 TCP `80`을 이 PC의 고정 내부 IPv4와 TCP `8010`으로, 외부 TCP `443`을 TCP `8443`으로 전달합니다. Windows 방화벽에도 TCP `8010`, `8443` 인바운드 허용 규칙이 필요합니다.

```text
http://your-hostname.ddns.net
  -> 공유기 공인 IP:80
    -> 이 PC의 내부 IP:8010
      -> Nginx:80
        -> FastAPI:8000
```

로그인과 JWT를 외부에 공개하기 전에는 HTTPS를 적용해야 합니다. Let's Encrypt HTTP-01 인증을 사용할 경우 외부 TCP `80` 연결이 반드시 Nginx까지 도달해야 하며, 인증서 적용 후 `PUBLIC_ORIGIN`과 Kakao 허용 도메인을 `https://...`로 변경합니다.

### 1. HTTP 부트스트랩

```powershell
docker compose -f compose.nginx.yml up -d --build
```

휴대전화 Wi-Fi를 끈 상태에서 `http://your-hostname.ddns.net/health`가 열리는지 먼저 확인합니다. 같은 공유기 안에서는 NAT loopback 미지원 때문에 도메인 접속이 실패할 수 있습니다.

### 2. 인증서 발급

외부 HTTP 접속이 확인된 다음 실행합니다.

```powershell
docker compose -f compose.nginx.yml --profile tools run --rm certbot `
  certonly --webroot --webroot-path /var/www/certbot `
  --domain your-hostname.ddns.net `
  --email your-email@example.com `
  --agree-tos --no-eff-email
```

### 3. HTTPS 전환

`project/.env`를 다음과 같이 변경합니다.

```dotenv
PUBLIC_ORIGIN=https://your-hostname.ddns.net
NGINX_CONFIG=./deploy/nginx-https.conf.template
```

설정을 다시 반영합니다.

```powershell
docker compose -f compose.nginx.yml up -d --force-recreate app nginx
docker compose -f compose.nginx.yml exec -T nginx nginx -t
```

이후 `https://your-hostname.ddns.net/health`와 HTTP에서 HTTPS로의 리다이렉트를 확인합니다.

### 4. 인증서 갱신

```powershell
docker compose -f compose.nginx.yml --profile tools run --rm certbot renew
docker compose -f compose.nginx.yml exec -T nginx nginx -s reload
```

인증서는 자동 만료 전에 위 명령을 실행하도록 Windows 작업 스케줄러에 등록해야 합니다.

## 포트포워딩 권한이 없는 네트워크

공유기 관리 권한이 없거나 통신사가 인바운드 포트를 차단한 환경에서는 No-IP가 DNS를 갱신해도 요청이 Nginx까지 도착하지 않습니다. 임시 시연 주소는 Cloudflare Quick Tunnel로 열 수 있습니다.

```powershell
docker compose -f compose.nginx.yml --profile tunnel up -d tunnel
docker compose -f compose.nginx.yml logs tunnel
```

로그에 출력된 `https://...trycloudflare.com` 주소의 호스트와 전체 출처를 `.env`에 설정한 뒤 앱을 다시 만듭니다.

```dotenv
TUNNEL_HOST=random-name.trycloudflare.com
TUNNEL_ORIGIN=https://random-name.trycloudflare.com
```

```powershell
docker compose -f compose.nginx.yml up -d --force-recreate app
```

Quick Tunnel 주소는 임시 주소이며 터널을 새로 만들면 변경될 수 있습니다. 고정 주소는 제어 가능한 공유기의 포트포워딩 또는 Cloudflare에서 관리하는 별도 도메인이 필요합니다.

## 실행

`project` 디렉터리에서 실행합니다.

```powershell
docker compose -f compose.nginx.yml up -d --build
docker compose -f compose.nginx.yml ps
```

- 서비스: `http://localhost:8010`
- 상태 확인: `http://localhost:8010/health`
- API 문서: `http://localhost:8010/docs`

## 로그와 재시작

```powershell
docker compose -f compose.nginx.yml logs -f app nginx
docker compose -f compose.nginx.yml restart
```

## 앱 컨테이너 중지

```powershell
docker compose -f compose.nginx.yml down
```

이 명령은 외부 PostgreSQL 컨테이너와 DB 볼륨을 삭제하지 않습니다.

## 공개 서버 전환

현재 설정은 로컬 시연용 HTTP 배포입니다. 인터넷에 공개할 때는 다음 설정이 추가로 필요합니다.

1. 서버 IP와 도메인의 DNS 연결
2. Nginx `server_name`을 실제 도메인으로 변경
3. TLS 인증서 적용 및 HTTP에서 HTTPS로 리다이렉트
4. `CORS_ORIGINS`, `ALLOWED_HOSTS`, Kakao JavaScript SDK 도메인을 실제 HTTPS 도메인으로 변경
5. DB 비밀번호 회전, 방화벽 설정, 자동 백업 구성
