/**
 * '다시, 공간' (Da-si Gong-gan) - Main Application Controller
 * 대구광역시 유휴시설 추천 및 매칭 플랫폼
 */

// =============================================================================
// 1. Application State & Storage
// =============================================================================

const STORAGE_KEYS = {
  SPACES: "dasi_gonggan_spaces",
  FAVORITES: "dasi_gonggan_favorites",
  APPLICATIONS: "dasi_gonggan_applications",
  VISITS: "dasi_gonggan_visits",
  THEME: "dasi_gonggan_theme",
  ROLE: "dasi_gonggan_role"
};

const appState = {
  spaces: [],
  favorites: new Set(),
  compareList: new Set(),
  applications: [],
  visits: [],
  currentRole: "GENERAL", // GENERAL | PROVIDER | ADMIN
  currentTab: "explore",  // explore | map | favorites | admin
  currentAdminTab: "spaces",
  theme: "dark",

  // Explorer Filters
  filters: {
    keyword: "",
    district: "전체",
    category: "ALL",
    maxRent: 100,
    minArea: 0,
    parking: false,
    remodeling: false,
    sortOrder: "recommended"
  },

  // Map Instance
  map: null,
  markersLayer: null,
  activePopupId: null,

  // AI Wizard State
  wzStep: 1,
  wzCriteria: {
    purpose: "STARTUP",
    districts: ["중구", "북구"],
    maxRent: 40,
    minArea: 60,
    tags: []
  }
};

// Initial Seed for Applications & Visits for realistic demo
const INITIAL_APPLICATIONS = [
  {
    id: "APP-2026-001",
    spaceId: "SPC-002",
    spaceName: "복현 혁신 청년 스타트업 코워킹 베이스",
    userName: "김민재",
    phone: "010-3342-8891",
    purpose: "STARTUP",
    purposeName: "청년 창업 및 기술 스타트업",
    plan: "대구 원도심 활성화를 위한 로컬 데이터 분석 및 생성형 AI 솔루션 개발팀 (총 4인)",
    period: "1년 (연장 가능)",
    teamSize: "3~5인",
    status: "REVIEWING",
    statusName: "검토 중",
    appliedAt: "2026-08-12"
  },
  {
    id: "APP-2026-002",
    spaceId: "SPC-001",
    spaceName: "삼덕 청년 예술창작 유휴창고",
    userName: "박서연",
    phone: "010-7761-4209",
    purpose: "ART",
    purposeName: "문화예술 전시 및 복합 창작",
    plan: "대구 근현대사를 테마로 한 청년 설치미술 전시 및 주말 시민 예술 워크숍 진행",
    period: "6개월",
    teamSize: "1~2인",
    status: "APPROVED",
    statusName: "승인 완료",
    appliedAt: "2026-08-10"
  }
];

const INITIAL_VISITS = [
  {
    id: "VST-2026-001",
    spaceId: "SPC-004",
    spaceName: "동성로 르네상스 팝업 & 소상공인 스토어",
    userName: "최동훈",
    phone: "010-5512-9901",
    date: "2026-08-20",
    time: "14:00",
    message: "동성로 통유리 파사드 실측 및 팝업스토어 전력 설비 점검 희망합니다.",
    status: "APPROVED",
    statusName: "방문 승인"
  },
  {
    id: "VST-2026-002",
    spaceId: "SPC-006",
    spaceName: "수성 알파시티 IT·소프트웨어 공유오피스",
    userName: "이지혜",
    phone: "010-8821-3310",
    date: "2026-08-22",
    time: "15:30",
    message: "서버랙실 인프라 및 회의실 방음 상태 사전 답사 요청",
    status: "PENDING",
    statusName: "승인 대기"
  }
];

// =============================================================================
// 2. Initialization
// =============================================================================

document.addEventListener("DOMContentLoaded", () => {
  loadStoredData();
  initTheme();
  initRole();
  initFilterUI();
  renderSpaceCards();
  updateMetrics();
  initMap();
  renderAdminTables();
});

function loadStoredData() {
  // Spaces
  const storedSpaces = localStorage.getItem(STORAGE_KEYS.SPACES);
  appState.spaces = storedSpaces ? JSON.parse(storedSpaces) : [...INITIAL_SPACES];

  // Favorites
  const storedFavs = localStorage.getItem(STORAGE_KEYS.FAVORITES);
  appState.favorites = storedFavs ? new Set(JSON.parse(storedFavs)) : new Set(["SPC-001", "SPC-002"]);

  // Applications
  const storedApps = localStorage.getItem(STORAGE_KEYS.APPLICATIONS);
  appState.applications = storedApps ? JSON.parse(storedApps) : [...INITIAL_APPLICATIONS];

  // Visits
  const storedVisits = localStorage.getItem(STORAGE_KEYS.VISITS);
  appState.visits = storedVisits ? JSON.parse(storedVisits) : [...INITIAL_VISITS];

  // Theme & Role
  appState.theme = localStorage.getItem(STORAGE_KEYS.THEME) || "dark";
  appState.currentRole = localStorage.getItem(STORAGE_KEYS.ROLE) || "GENERAL";
}

function saveData(key) {
  if (key === STORAGE_KEYS.SPACES) {
    localStorage.setItem(STORAGE_KEYS.SPACES, JSON.stringify(appState.spaces));
  } else if (key === STORAGE_KEYS.FAVORITES) {
    localStorage.setItem(STORAGE_KEYS.FAVORITES, JSON.stringify(Array.from(appState.favorites)));
  } else if (key === STORAGE_KEYS.APPLICATIONS) {
    localStorage.setItem(STORAGE_KEYS.APPLICATIONS, JSON.stringify(appState.applications));
  } else if (key === STORAGE_KEYS.VISITS) {
    localStorage.setItem(STORAGE_KEYS.VISITS, JSON.stringify(appState.visits));
  }
}

// =============================================================================
// 3. Theme & Role Management
// =============================================================================

function initTheme() {
  document.documentElement.setAttribute("data-theme", appState.theme);
  const icon = document.querySelector("#theme-toggle-btn i");
  if (icon) {
    icon.className = appState.theme === "dark" ? "fa-solid fa-sun" : "fa-solid fa-moon";
  }
}

function toggleTheme() {
  appState.theme = appState.theme === "dark" ? "light" : "dark";
  localStorage.setItem(STORAGE_KEYS.THEME, appState.theme);
  initTheme();
  showToast(appState.theme === "dark" ? "다크 모드가 적용되었습니다." : "라이트 모드가 적용되었습니다.", "info");
}

function initRole() {
  setUserRole(appState.currentRole, false);
}

function setUserRole(role, notify = true) {
  appState.currentRole = role;
  localStorage.setItem(STORAGE_KEYS.ROLE, role);

  document.querySelectorAll(".role-pill").forEach(el => el.classList.remove("active"));
  const activePill = document.getElementById(`role-${role.toLowerCase()}`);
  if (activePill) activePill.classList.add("active");

  const quickRegisterBtn = document.getElementById("btn-quick-register");
  if (quickRegisterBtn) {
    quickRegisterBtn.style.display = (role === "ADMIN" || role === "PROVIDER") ? "flex" : "none";
  }

  if (notify) {
    const roleLabels = {
      GENERAL: "청년/일반 사용자 모드로 전환되었습니다. (공간 탐색, AI 추천, 신청)",
      PROVIDER: "공간 제공자 모드로 전환되었습니다. (유휴시설 등록 및 관리)",
      ADMIN: "대구시 관리자 모드로 전환되었습니다. (전체 심사 및 공공데이터 제어)"
    };
    showToast(roleLabels[role] || "역할이 변경되었습니다.", "success");
  }
}

// =============================================================================
// 4. Navigation & Tab Switching
// =============================================================================

function switchNavTab(tabName) {
  appState.currentTab = tabName;

  document.querySelectorAll(".nav-tab-btn").forEach(btn => btn.classList.remove("active"));
  const activeBtn = document.getElementById(`tab-${tabName}`);
  if (activeBtn) activeBtn.classList.add("active");

  document.querySelectorAll(".tab-view-section").forEach(sec => sec.style.display = "none");

  const targetSection = document.getElementById(`view-${tabName}`);
  if (targetSection) {
    targetSection.style.display = "block";
  }

  if (tabName === "map") {
    setTimeout(() => {
      if (appState.map) {
        appState.map.invalidateSize();
        fitMapToMarkers();
      }
    }, 200);
    renderMapSideList(getFilteredSpaces());
  } else if (tabName === "favorites") {
    renderFavorites();
  } else if (tabName === "admin") {
    renderAdminTables();
  }
}

// =============================================================================
// 5. Filter Controls & Search Engine
// =============================================================================

function initFilterUI() {
  // District Chips
  const districtContainer = document.getElementById("district-chips");
  if (districtContainer) {
    districtContainer.innerHTML = `
      <button class="chip-btn active" onclick="selectDistrict('전체', this)">전체</button>
      ${COMMON_CODES.DISTRICTS.map(d => `
        <button class="chip-btn" onclick="selectDistrict('${d}', this)">${d}</button>
      `).join("")}
    `;
  }

  // Category Selector
  const catContainer = document.getElementById("category-selector");
  if (catContainer) {
    catContainer.innerHTML = `
      <div class="cat-select-card active" onclick="selectCategory('ALL', this)">
        <i class="fa-solid fa-border-all" style="color:var(--primary);"></i> 전체 용도
      </div>
      ${COMMON_CODES.CATEGORIES.map(c => `
        <div class="cat-select-card" onclick="selectCategory('${c.code}', this)">
          <i class="fa-solid fa-${c.icon}" style="color:${c.color};"></i> ${c.name}
        </div>
      `).join("")}
    `;
  }
}

function selectDistrict(dist, elem) {
  appState.filters.district = dist;
  document.querySelectorAll("#district-chips .chip-btn").forEach(b => b.classList.remove("active"));
  elem.classList.add("active");
  document.getElementById("selected-district-count").textContent = dist;
  applyFilters();
}

function selectCategory(catCode, elem) {
  appState.filters.category = catCode;
  document.querySelectorAll("#category-selector .cat-select-card").forEach(b => b.classList.remove("active"));
  elem.classList.add("active");
  applyFilters();
}

function updateRentDisplay(val) {
  appState.filters.maxRent = parseInt(val);
  const label = parseInt(val) >= 100 ? "전체 (제한없음)" : `최대 ${val}만원 이하`;
  document.getElementById("display-max-rent").textContent = label;
  applyFilters();
}

function updateAreaDisplay(val) {
  appState.filters.minArea = parseInt(val);
  const pyeong = Math.round(val / 3.3);
  const label = parseInt(val) === 0 ? "전체 (0㎡ 이상)" : `최소 ${val}㎡ (${pyeong}평) 이상`;
  document.getElementById("display-min-area").textContent = label;
  applyFilters();
}

function resetFilters() {
  appState.filters = {
    keyword: "",
    district: "전체",
    category: "ALL",
    maxRent: 100,
    minArea: 0,
    parking: false,
    remodeling: false,
    sortOrder: "recommended"
  };

  document.getElementById("filter-keyword").value = "";
  document.getElementById("filter-max-rent").value = "100";
  document.getElementById("filter-min-area").value = "0";
  document.getElementById("filter-parking").checked = false;
  document.getElementById("filter-remodeling").checked = false;
  document.getElementById("sort-order").value = "recommended";
  document.getElementById("display-max-rent").textContent = "전체 (제한없음)";
  document.getElementById("display-min-area").textContent = "전체 (0㎡ 이상)";
  document.getElementById("selected-district-count").textContent = "전체";

  document.querySelectorAll("#district-chips .chip-btn").forEach((b, idx) => {
    b.classList.toggle("active", idx === 0);
  });
  document.querySelectorAll("#category-selector .cat-select-card").forEach((b, idx) => {
    b.classList.toggle("active", idx === 0);
  });

  applyFilters();
  showToast("필터가 초기화되었습니다.", "info");
}

function getFilteredSpaces() {
  const { keyword, district, category, maxRent, minArea, parking, remodeling, sortOrder } = appState.filters;

  return appState.spaces.filter(s => {
    // Keyword
    if (keyword.trim()) {
      const q = keyword.toLowerCase();
      const matchText = (s.name + s.address + s.description + s.tags.join(" ") + s.managingAgency).toLowerCase();
      if (!matchText.includes(q)) return false;
    }

    // District
    if (district !== "전체" && s.district !== district) return false;

    // Category
    if (category !== "ALL" && s.category !== category) return false;

    // Max Rent
    if (maxRent < 100 && s.monthlyRent > maxRent) return false;

    // Min Area
    if (minArea > 0 && s.area < minArea) return false;

    // Parking
    if (parking && !s.parking) return false;

    // Remodeling
    if (remodeling && s.remodelingStatus !== "SUPPORT_ELIGIBLE" && s.remodelingStatus !== "COMPLETED") return false;

    return true;
  }).sort((a, b) => {
    if (sortOrder === "views") return b.views - a.views;
    if (sortOrder === "price-asc") return a.monthlyRent - b.monthlyRent;
    if (sortOrder === "price-desc") return b.monthlyRent - a.monthlyRent;
    if (sortOrder === "area-desc") return b.area - a.area;
    if (sortOrder === "latest") return new Date(b.createdAt) - new Date(a.createdAt);
    return b.favoriteCount - a.favoriteCount; // recommended
  });
}

function applyFilters() {
  appState.filters.keyword = document.getElementById("filter-keyword").value;
  appState.filters.parking = document.getElementById("filter-parking").checked;
  appState.filters.remodeling = document.getElementById("filter-remodeling").checked;
  appState.filters.sortOrder = document.getElementById("sort-order").value;

  const filtered = getFilteredSpaces();
  document.getElementById("search-count").textContent = filtered.length;
  renderSpaceCards(filtered);

  if (appState.currentTab === "map") {
    updateMapMarkers(filtered);
    renderMapSideList(filtered);
  }
}

// =============================================================================
// 6. Space Cards Rendering (Explorer & Favorites)
// =============================================================================

function renderSpaceCards(spaces = null) {
  const container = document.getElementById("spaces-grid");
  if (!container) return;

  const items = spaces || getFilteredSpaces();
  document.getElementById("search-count").textContent = items.length;

  if (items.length === 0) {
    container.innerHTML = `
      <div style="grid-column:1/-1; text-align:center; padding:4rem 2rem; background:var(--bg-glass); border-radius:var(--radius-lg); border:1px solid var(--border-glass);">
        <i class="fa-solid fa-triangle-exclamation" style="font-size:3rem; color:#F59E0B; margin-bottom:1rem;"></i>
        <h3 style="font-size:1.25rem; font-weight:700; margin-bottom:0.5rem;">조건에 맞는 유휴공간이 없습니다</h3>
        <p style="color:var(--text-muted); font-size:0.9rem; margin-bottom:1.5rem;">필터 조건을 완화하거나 초기화하여 다른 공간을 검색해보세요.</p>
        <button class="btn-primary" style="margin:0 auto;" onclick="resetFilters()">필터 초기화</button>
      </div>
    `;
    return;
  }

  container.innerHTML = items.map(s => createSpaceCardHTML(s)).join("");
  updateFavoriteBadge();
}

function createSpaceCardHTML(s, isRec = false, matchScore = null, matchReasons = []) {
  const isFav = appState.favorites.has(s.id);
  const isCompared = appState.compareList.has(s.id);

  let statusBadgeClass = "badge-success";
  if (s.status === "RESERVED") statusBadgeClass = "badge-warning";
  if (s.status === "IN_USE") statusBadgeClass = "badge-info";
  if (s.status === "REMODELING") statusBadgeClass = "badge-purple";
  if (s.status === "UNAVAILABLE") statusBadgeClass = "badge-danger";

  return `
    <div class="space-card" data-id="${s.id}">
      <div class="card-image-wrap">
        <img src="${s.photos[0]}" alt="${s.name}" loading="lazy">
        <div class="card-badges-top">
          <span class="card-badge badge-cat">${s.categoryName}</span>
          <span class="card-badge badge-district">${s.district}</span>
        </div>
        <span class="badge-status ${statusBadgeClass}">${s.statusName}</span>
        
        <button class="btn-fav-card ${isFav ? 'active' : ''}" onclick="toggleFavorite('${s.id}', event)" title="관심 공간 찜하기">
          <i class="${isFav ? 'fa-solid' : 'fa-regular'} fa-heart"></i>
        </button>

        ${isRec && matchScore ? `
          <div class="match-score-pill">
            <i class="fa-solid fa-bolt"></i> 적합도 ${matchScore}%
          </div>
        ` : ''}
      </div>

      <div class="card-body">
        <h3 class="card-title">${s.name}</h3>
        <p class="card-address">
          <i class="fa-solid fa-location-dot" style="color:var(--primary);"></i> ${s.address}
        </p>

        <div class="card-specs">
          <div class="spec-item">
            <span>면적</span> <strong>${s.area}㎡ (${s.pyeong}평)</strong>
          </div>
          <div style="color:var(--border-glass);">|</div>
          <div class="spec-item">
            <span>주차</span> <strong>${s.parking ? s.parkingSpaces + '대 가능' : '불가'}</strong>
          </div>
        </div>

        ${matchReasons && matchReasons.length > 0 ? `
          <div style="margin-bottom:0.5rem;">
            <span style="font-size:0.75rem; color:#818CF8; font-weight:700;">✨ 매칭 이유: </span>
            <span style="font-size:0.75rem; color:var(--text-muted);">${matchReasons.join(' · ')}</span>
          </div>
        ` : ''}

        <div class="card-tags">
          ${s.tags.slice(0, 3).map(t => `<span class="tag-item">#${t}</span>`).join("")}
        </div>

        <div class="card-price-row">
          <div>
            <div class="price-main">
              ${s.monthlyRent === 0 ? '무상지원' : '월 ' + s.monthlyRent + '만원'}
              <span> / 관리비 ${s.maintenanceFee}만</span>
            </div>
            <div class="price-deposit">보증금 ${s.deposit}만원</div>
          </div>
        </div>

        <div class="card-footer-actions">
          <button class="btn-card-detail" onclick="openSpaceDetail('${s.id}')">
            <i class="fa-solid fa-magnifying-glass-plus"></i> 상세 보기
          </button>
          <button class="btn-card-compare ${isCompared ? 'active' : ''}" onclick="toggleCompareItem('${s.id}', this)" title="비교함 담기">
            <i class="fa-solid fa-code-compare"></i> ${isCompared ? '담김' : '비교'}
          </button>
        </div>
      </div>
    </div>
  `;
}

function renderFavorites() {
  const container = document.getElementById("favorites-grid");
  if (!container) return;

  const favSpaces = appState.spaces.filter(s => appState.favorites.has(s.id));
  if (favSpaces.length === 0) {
    container.innerHTML = `
      <div style="grid-column:1/-1; text-align:center; padding:4rem 2rem; background:var(--bg-glass); border-radius:var(--radius-lg); border:1px solid var(--border-glass);">
        <i class="fa-regular fa-heart" style="font-size:3rem; color:var(--text-dim); margin-bottom:1rem;"></i>
        <h3 style="font-size:1.25rem; font-weight:700; margin-bottom:0.5rem;">찜한 관심 공간이 없습니다</h3>
        <p style="color:var(--text-muted); font-size:0.9rem; margin-bottom:1.5rem;">마음에 드는 대구 유휴공간의 하트 아이콘을 눌러 저장해보세요.</p>
        <button class="btn-primary" style="margin:0 auto;" onclick="switchNavTab('explore')">공간 둘러보기</button>
      </div>
    `;
    return;
  }

  container.innerHTML = favSpaces.map(s => createSpaceCardHTML(s)).join("");
}

function toggleFavorite(spaceId, event) {
  if (event) event.stopPropagation();

  if (appState.favorites.has(spaceId)) {
    appState.favorites.delete(spaceId);
    showToast("관심 공간에서 제외되었습니다.", "info");
  } else {
    appState.favorites.add(spaceId);
    showToast("관심 공간으로 저장되었습니다.", "success");
  }

  saveData(STORAGE_KEYS.FAVORITES);
  updateFavoriteBadge();
  applyFilters();

  if (appState.currentTab === "favorites") {
    renderFavorites();
  }
}

function updateFavoriteBadge() {
  const badge = document.getElementById("fav-count-badge");
  if (badge) {
    badge.textContent = appState.favorites.size;
  }
}

// =============================================================================
// 7. Multi-Space Comparison (Compare Matrix)
// =============================================================================

function toggleCompareItem(spaceId, btn) {
  if (appState.compareList.has(spaceId)) {
    appState.compareList.delete(spaceId);
    btn.classList.remove("active");
    btn.innerHTML = `<i class="fa-solid fa-code-compare"></i> 비교`;
    showToast("비교함에서 제거되었습니다.", "info");
  } else {
    if (appState.compareList.size >= 4) {
      showToast("비교함에는 최대 4개 공간까지만 담을 수 있습니다.", "warning");
      return;
    }
    appState.compareList.add(spaceId);
    btn.classList.add("active");
    btn.innerHTML = `<i class="fa-solid fa-code-compare"></i> 담김`;
    showToast("비교함에 담겼습니다. 아래 바에서 비교해보세요.", "success");
  }

  updateCompareDrawer();
}

function updateCompareDrawer() {
  const drawer = document.getElementById("floating-compare-bar");
  const countLabel = document.getElementById("compare-count");

  if (appState.compareList.size > 0) {
    drawer.classList.add("show");
    countLabel.textContent = appState.compareList.size;
  } else {
    drawer.classList.remove("show");
  }
}

function clearCompareList() {
  appState.compareList.clear();
  updateCompareDrawer();
  document.querySelectorAll(".btn-card-compare").forEach(b => {
    b.classList.remove("active");
    b.innerHTML = `<i class="fa-solid fa-code-compare"></i> 비교`;
  });
  showToast("비교함이 비워졌습니다.", "info");
}

function openCompareModal() {
  if (appState.compareList.size < 2 && appState.currentTab !== "favorites") {
    showToast("비교를 위해 최소 2개 이상의 공간을 선택해주세요.", "warning");
    return;
  }

  let targetIds = Array.from(appState.compareList);
  if (targetIds.length === 0 && appState.currentTab === "favorites") {
    targetIds = Array.from(appState.favorites).slice(0, 4);
  }

  if (targetIds.length < 2) {
    showToast("비교할 공간이 부족합니다. 2개 이상 선택해주세요.", "warning");
    return;
  }

  const compareSpaces = appState.spaces.filter(s => targetIds.includes(s.id));
  const tableContainer = document.getElementById("compare-table-container");

  tableContainer.innerHTML = `
    <table class="compare-table">
      <thead>
        <tr>
          <th>구분 항목</th>
          ${compareSpaces.map(s => `
            <th>
              <div style="font-size:1rem; font-weight:800; color:var(--text-bright);">${s.name}</div>
              <span style="font-size:0.75rem; color:var(--primary);">${s.district} / ${s.categoryName}</span>
            </th>
          `).join("")}
        </tr>
      </thead>
      <tbody>
        <tr>
          <th>대표 이미지</th>
          ${compareSpaces.map(s => `
            <td><img src="${s.photos[0]}" style="width:100%; height:120px; object-fit:cover; border-radius:6px;"></td>
          `).join("")}
        </tr>
        <tr>
          <th>월 임대료 / 보증금</th>
          ${compareSpaces.map(s => `
            <td><strong style="color:#10B981; font-size:1.1rem;">월 ${s.monthlyRent}만원</strong> (보증금 ${s.deposit}만)</td>
          `).join("")}
        </tr>
        <tr>
          <th>전용 면적</th>
          ${compareSpaces.map(s => `
            <td><strong>${s.area} ㎡</strong> (약 ${s.pyeong}평)</td>
          `).join("")}
        </tr>
        <tr>
          <th>층수 및 구조</th>
          ${compareSpaces.map(s => `
            <td>${s.floor}<br><span style="font-size:0.75rem; color:var(--text-muted);">${s.structure}</span></td>
          `).join("")}
        </tr>
        <tr>
          <th>주차 여부</th>
          ${compareSpaces.map(s => `
            <td>${s.parking ? '✅ 전용 ' + s.parkingSpaces + '대 가능' : '❌ 불가'}</td>
          `).join("")}
        </tr>
        <tr>
          <th>도시재생 지원정책</th>
          ${compareSpaces.map(s => `
            <td><span style="color:#818CF8; font-size:0.82rem;">${s.remodelingSupport}</span></td>
          `).join("")}
        </tr>
        <tr>
          <th>주요 유틸리티</th>
          ${compareSpaces.map(s => `
            <td><div style="display:flex; flex-wrap:wrap; gap:4px;">${s.utilities.map(u => `<span class="utility-chip" style="font-size:0.7rem; padding:2px 6px;">${u}</span>`).join("")}</div></td>
          `).join("")}
        </tr>
        <tr>
          <th>관리기관</th>
          ${compareSpaces.map(s => `
            <td>${s.managingAgency}<br><span style="font-size:0.75rem; color:var(--text-dim);">${s.agencyContact}</span></td>
          `).join("")}
        </tr>
        <tr>
          <th>신청 액션</th>
          ${compareSpaces.map(s => `
            <td>
              <button class="btn-primary" style="width:100%; font-size:0.8rem; padding:0.45rem;" onclick="closeModal('modal-compare-matrix'); openSpaceDetail('${s.id}')">
                상세보기 및 신청
              </button>
            </td>
          `).join("")}
        </tr>
      </tbody>
    </table>
  `;

  openModal("modal-compare-matrix");
}

// =============================================================================
// 8. Space Detail View & Modal (SPACE-02, FR-040~045)
// =============================================================================

function openSpaceDetail(spaceId) {
  const space = appState.spaces.find(s => s.id === spaceId);
  if (!space) return;

  // Increase views
  space.views = (space.views || 0) + 1;
  saveData(STORAGE_KEYS.SPACES);

  const isFav = appState.favorites.has(space.id);
  const container = document.getElementById("detail-modal-content");

  container.innerHTML = `
    <!-- Gallery -->
    <div class="detail-gallery">
      <div class="gallery-main">
        <img id="detail-main-img" src="${space.photos[0]}" alt="${space.name}">
      </div>
      <div class="gallery-thumbs">
        ${space.photos.map((p, idx) => `
          <img src="${p}" onclick="document.getElementById('detail-main-img').src='${p}'" alt="Thumb ${idx+1}">
        `).join("")}
      </div>
    </div>

    <!-- Header Section -->
    <div class="detail-header-section">
      <div class="detail-title-wrap">
        <div style="display:flex; gap:6px; margin-bottom:6px;">
          <span class="card-badge badge-cat">${space.categoryName}</span>
          <span class="card-badge badge-district">${space.district}</span>
          <span class="badge-status badge-success">${space.statusName}</span>
        </div>
        <h2>${space.name}</h2>
        <p><i class="fa-solid fa-location-dot" style="color:var(--primary);"></i> ${space.address}</p>
      </div>

      <div class="detail-price-box">
        <div style="font-size:0.8rem; color:var(--text-muted);">월 임대료</div>
        <div class="price-lg">${space.monthlyRent === 0 ? '무상지원' : '월 ' + space.monthlyRent + '만원'}</div>
        <div style="font-size:0.8rem; color:var(--text-dim);">보증금 ${space.deposit}만원 / 관리비 ${space.maintenanceFee}만원</div>
      </div>
    </div>

    <!-- Policy & Remodeling Support Banner -->
    <div class="policy-support-banner">
      <i class="fa-solid fa-hand-holding-dollar policy-icon"></i>
      <div class="policy-text">
        <h5>대구광역시 도시재생 및 청년 창업 지원 정책 적용 대상</h5>
        <p>${space.remodelingSupport}</p>
      </div>
    </div>

    <!-- Specs Grid -->
    <div class="detail-specs-table">
      <div class="spec-row"><span class="label">전용 면적</span><span class="val">${space.area} ㎡ (${space.pyeong} 평)</span></div>
      <div class="spec-row"><span class="label">층수 / 층고</span><span class="val">${space.floor}</span></div>
      <div class="spec-row"><span class="label">건물 구조</span><span class="val">${space.structure}</span></div>
      <div class="spec-row"><span class="label">주차 시설</span><span class="val">${space.parking ? '전용 ' + space.parkingSpaces + '대 주차 가능' : '인근 공영주차장 이용'}</span></div>
      <div class="spec-row"><span class="label">대중교통</span><span class="val">${space.transportInfo}</span></div>
      <div class="spec-row"><span class="label">관리 주체</span><span class="val">${space.managingAgency} (${space.agencyContact})</span></div>
    </div>

    <!-- Utility Badges -->
    <h4 style="font-size:0.95rem; font-weight:700; margin-bottom:0.5rem;">시설 및 인프라 구비 내역</h4>
    <div class="detail-utilities-list">
      ${space.utilities.map(u => `<div class="utility-chip"><i class="fa-solid fa-check" style="color:var(--primary);"></i> ${u}</div>`).join("")}
    </div>

    <!-- Description -->
    <h4 style="font-size:0.95rem; font-weight:700; margin-bottom:0.5rem;">공간 소개 및 추천 활용 방안</h4>
    <div class="detail-desc-text">
      ${space.description}
    </div>

    ${space.features && space.features.length > 0 ? `
      <h4 style="font-size:0.95rem; font-weight:700; margin-bottom:0.5rem;">핵심 입주 혜택</h4>
      <ul style="padding-left:1.25rem; font-size:0.88rem; color:var(--text-muted); margin-bottom:1.5rem; line-height:1.7;">
        ${space.features.map(f => `<li>${f}</li>`).join("")}
      </ul>
    ` : ''}

    <!-- Action Buttons -->
    <div class="detail-actions-bar">
      <button class="btn-outline" onclick="toggleFavorite('${space.id}', event)">
        <i class="${isFav ? 'fa-solid' : 'fa-regular'} fa-heart" style="color:${isFav ? '#EF4444' : 'inherit'};"></i>
        ${isFav ? '관심 공간 해제' : '관심 공간 찜하기'}
      </button>

      <button class="btn-outline" style="margin-left:auto;" onclick="openVisitBookingModal('${space.id}')">
        <i class="fa-solid fa-calendar-days"></i> 현장 투어 예약
      </button>

      <button class="btn-primary" onclick="openSpaceAppModal('${space.id}')">
        <i class="fa-solid fa-file-signature"></i> 공간 이용 신청서 제출
      </button>
    </div>
  `;

  openModal("modal-space-detail");
}

// =============================================================================
// 9. Interactive Daegu Map (Leaflet Map Engine)
// =============================================================================

function initMap() {
  const mapElement = document.getElementById("daegu-map");
  if (!mapElement) return;

  // Daegu Center Coordinates
  appState.map = L.map('daegu-map').setView([35.8714, 128.6014], 12);

  // CartoDB Dark Matter Tiles (Sleek Dark Map)
  L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 19
  }).addTo(appState.map);

  appState.markersLayer = L.layerGroup().addTo(appState.map);
  updateMapMarkers(appState.spaces);
}

function updateMapMarkers(spaces) {
  if (!appState.markersLayer) return;
  appState.markersLayer.clearLayers();

  spaces.forEach(s => {
    const customIcon = L.divIcon({
      className: 'custom-leaflet-pin',
      html: `
        <div class="custom-map-marker">
          <i class="fa-solid fa-cube"></i>
          <span>${s.name.split(' ')[0]}</span>
          <span style="color:var(--primary); font-size:0.75rem;">${s.monthlyRent === 0 ? '무상' : s.monthlyRent + '만'}</span>
        </div>
      `,
      iconSize: [120, 36],
      iconAnchor: [60, 18]
    });

    const marker = L.marker([s.lat, s.lng], { icon: customIcon }).addTo(appState.markersLayer);

    marker.bindPopup(`
      <div style="font-family:'Pretendard', sans-serif; min-width:200px; padding:4px;">
        <img src="${s.photos[0]}" style="width:100%; height:90px; object-fit:cover; border-radius:4px; margin-bottom:6px;">
        <div style="font-weight:700; font-size:0.9rem; color:#0F172A;">${s.name}</div>
        <div style="font-size:0.75rem; color:#64748B; margin-bottom:4px;">${s.district} · ${s.categoryName}</div>
        <div style="font-weight:800; font-size:0.95rem; color:#0D9488; margin-bottom:8px;">
          ${s.monthlyRent === 0 ? '무상지원' : '월 ' + s.monthlyRent + '만원'} (보증금 ${s.deposit}만)
        </div>
        <button onclick="openSpaceDetail('${s.id}')" style="width:100%; background:#0D9488; color:white; border:none; padding:6px; border-radius:4px; font-weight:700; font-size:0.8rem; cursor:pointer;">
          상세보기
        </button>
      </div>
    `);
  });
}

function renderMapSideList(spaces) {
  const container = document.getElementById("map-side-items");
  if (!container) return;

  container.innerHTML = spaces.map(s => `
    <div class="map-side-card" onclick="focusMapOnSpace('${s.id}', ${s.lat}, ${s.lng})">
      <img src="${s.photos[0]}" alt="${s.name}">
      <div class="map-side-info">
        <h4>${s.name}</h4>
        <p>${s.district} · ${s.categoryName}</p>
        <div class="price">${s.monthlyRent === 0 ? '무상지원' : '월 ' + s.monthlyRent + '만원'}</div>
      </div>
    </div>
  `).join("");
}

function focusMapOnSpace(spaceId, lat, lng) {
  if (appState.map) {
    appState.map.flyTo([lat, lng], 15, { duration: 1 });
  }
}

function fitMapToMarkers() {
  if (!appState.map) return;
  const filtered = getFilteredSpaces();
  if (filtered.length === 0) return;

  const bounds = L.latLngBounds(filtered.map(s => [s.lat, s.lng]));
  appState.map.fitBounds(bounds, { padding: [50, 50] });
}

// =============================================================================
// 10. AI Smart Recommendation Engine (REC-01, FR-030~034)
// =============================================================================

function openRecommendWizard() {
  appState.wzStep = 1;
  updateWizardUI();

  // Populate District chips for Wizard
  const container = document.getElementById("wz-district-chips");
  if (container) {
    container.innerHTML = COMMON_CODES.DISTRICTS.map(d => `
      <button class="chip-btn ${appState.wzCriteria.districts.includes(d) ? 'active' : ''}" onclick="toggleWizardDistrict('${d}', this)">${d}</button>
    `).join("");
  }

  openModal("modal-recommend-wizard");
}

function selectWizardOpt(group, val, elem) {
  appState.wzCriteria[group] = val;
  elem.parentElement.querySelectorAll(".wizard-opt-card").forEach(c => c.classList.remove("selected"));
  elem.classList.add("selected");
}

function toggleWizardDistrict(d, elem) {
  const list = appState.wzCriteria.districts;
  if (list.includes(d)) {
    appState.wzCriteria.districts = list.filter(item => item !== d);
    elem.classList.remove("active");
  } else {
    list.push(d);
    elem.classList.add("active");
  }
}

function toggleWizardTag(tag, elem) {
  const tags = appState.wzCriteria.tags;
  if (tags.includes(tag)) {
    appState.wzCriteria.tags = tags.filter(t => t !== tag);
    elem.classList.remove("selected");
  } else {
    tags.push(tag);
    elem.classList.add("selected");
  }
}

function updateWizardUI() {
  const step = appState.wzStep;

  // Step Indicators
  document.getElementById("wz-step-indicator").textContent = `Step ${step} / 4`;
  for (let i = 1; i <= 4; i++) {
    const bar = document.getElementById(`wz-prog-${i}`);
    if (bar) bar.classList.toggle("active", i <= step);
    const stepEl = document.getElementById(`wz-step-${i}`);
    if (stepEl) stepEl.classList.toggle("active", i === step);
  }

  // Prev & Next Buttons
  document.getElementById("wz-btn-prev").style.display = step > 1 ? "block" : "none";
  const nextBtn = document.getElementById("wz-btn-next");
  if (step === 4) {
    nextBtn.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> AI 맞춤 공간 매칭 결과 보기`;
  } else {
    nextBtn.innerHTML = `다음 단계 <i class="fa-solid fa-chevron-right"></i>`;
  }
}

function prevWizardStep() {
  if (appState.wzStep > 1) {
    appState.wzStep--;
    updateWizardUI();
  }
}

function nextWizardStep() {
  if (appState.wzStep < 4) {
    appState.wzStep++;
    updateWizardUI();
  } else {
    // Run AI Matching Calculation
    closeModal("modal-recommend-wizard");
    executeAIMatching();
  }
}

/**
 * AI Matching Engine: Calculates Match Score (0~100) & Explanatory Reasons
 */
function calculateMatchScore(space, criteria) {
  let score = 0;
  const reasons = [];

  // 1. Purpose / Category match (35 pts)
  if (space.category === criteria.purpose) {
    score += 35;
    reasons.push(`${space.categoryName} 특화 시설`);
  } else {
    score += 15;
  }

  // 2. District Match (25 pts)
  if (criteria.districts.length === 0 || criteria.districts.includes(space.district)) {
    score += 25;
    reasons.push(`${space.district} 선호 지역 일치`);
  } else {
    score += 5;
  }

  // 3. Rent / Budget Match (20 pts)
  if (space.monthlyRent <= criteria.maxRent) {
    score += 20;
    reasons.push(`희망 예산 (${criteria.maxRent}만원) 충족`);
  } else if (space.monthlyRent <= criteria.maxRent + 10) {
    score += 10;
  }

  // 4. Area Match (10 pts)
  if (space.area >= criteria.minArea) {
    score += 10;
    reasons.push(`면적 (${criteria.minArea}㎡) 요건 적합`);
  } else {
    score += 5;
  }

  // 5. Special Tags Match (10 pts)
  if (criteria.tags.includes("parking") && space.parking) {
    score += 5;
    reasons.push("전용 주차 완비");
  }
  if (criteria.tags.includes("remodeling") && (space.remodelingStatus === "SUPPORT_ELIGIBLE" || space.remodelingStatus === "COMPLETED")) {
    score += 5;
    reasons.push("도시재생 보조금 혜택");
  }

  // Cap at 98% for realistic AI matching feel
  const finalScore = Math.min(score, 98);
  return { score: finalScore, reasons };
}

function executeAIMatching() {
  showToast("AI 매칭 알고리즘이 대구 유휴공간 적합도를 분석 중입니다...", "info");

  setTimeout(() => {
    switchNavTab("explore");

    const scoredSpaces = appState.spaces.map(s => {
      const match = calculateMatchScore(s, appState.wzCriteria);
      return {
        ...s,
        matchScore: match.score,
        matchReasons: match.reasons
      };
    }).sort((a, b) => b.matchScore - a.matchScore);

    const container = document.getElementById("spaces-grid");
    container.innerHTML = `
      <div style="grid-column:1/-1; background:linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(13, 148, 136, 0.15) 100%); border:1px solid rgba(99, 102, 241, 0.4); border-radius:var(--radius-lg); padding:1.25rem 1.5rem; display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
        <div>
          <h3 style="font-size:1.15rem; font-weight:800; color:#818CF8;">
            <i class="fa-solid fa-wand-magic-sparkles"></i> AI 맞춤 추천 결과 (적합도 순 정렬)
          </h3>
          <p style="font-size:0.85rem; color:var(--text-muted); margin-top:2px;">
            선택 조건: ${appState.wzCriteria.purpose} 용도 · ${appState.wzCriteria.districts.join(", ")} · 월 ${appState.wzCriteria.maxRent}만 이하 · ${appState.wzCriteria.minArea}㎡ 이상
          </p>
        </div>
        <button class="btn-outline" onclick="applyFilters()" style="font-size:0.8rem;">
          <i class="fa-solid fa-rotate-left"></i> 전체 목록 복원
        </button>
      </div>
      ${scoredSpaces.map(s => createSpaceCardHTML(s, true, s.matchScore, s.matchReasons)).join("")}
    `;

    document.getElementById("search-count").textContent = scoredSpaces.length;
    showToast("최적의 매칭 추천 공간 12개소가 산출되었습니다!", "success");
  }, 600);
}

// =============================================================================
// 11. Visit Booking & Space Application Forms (VISIT-01, MATCH-01)
// =============================================================================

function openVisitBookingModal(spaceId) {
  closeModal("modal-space-detail");
  const space = appState.spaces.find(s => s.id === spaceId);
  if (!space) return;

  document.getElementById("visit-space-id").value = space.id;
  document.getElementById("visit-space-name-label").textContent = `대상 공간: ${space.name} (${space.district})`;

  // Set default date to tomorrow
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  document.getElementById("visit-date").value = tomorrow.toISOString().split("T")[0];

  openModal("modal-visit-booking");
}

function submitVisitBooking(e) {
  e.preventDefault();
  const spaceId = document.getElementById("visit-space-id").value;
  const space = appState.spaces.find(s => s.id === spaceId);

  const newVisit = {
    id: "VST-2026-" + String(appState.visits.length + 1).padStart(3, "0"),
    spaceId: spaceId,
    spaceName: space ? space.name : "유휴공간",
    userName: document.getElementById("visit-user-name").value,
    phone: document.getElementById("visit-user-phone").value,
    date: document.getElementById("visit-date").value,
    time: document.getElementById("visit-time").value,
    message: document.getElementById("visit-message").value || "특이사항 없음",
    status: "PENDING",
    statusName: "승인 대기"
  };

  appState.visits.unshift(newVisit);
  saveData(STORAGE_KEYS.VISITS);

  closeModal("modal-visit-booking");
  showToast(`[${newVisit.id}] 현장 투어 방문 예약이 정상 접수되었습니다! 관리자 승인 후 안내드립니다.`, "success");
  renderAdminTables();
  updateMetrics();
}

function openSpaceAppModal(spaceId) {
  closeModal("modal-space-detail");
  const space = appState.spaces.find(s => s.id === spaceId);
  if (!space) return;

  document.getElementById("apply-space-id").value = space.id;
  document.getElementById("apply-space-name-label").textContent = `신청 대상: ${space.name} (${space.district} / ${space.categoryName})`;
  document.getElementById("apply-purpose").value = space.category;

  openModal("modal-space-application");
}

function submitSpaceApplication(e) {
  e.preventDefault();
  const spaceId = document.getElementById("apply-space-id").value;
  const space = appState.spaces.find(s => s.id === spaceId);

  const newApp = {
    id: "APP-2026-" + String(appState.applications.length + 1).padStart(3, "0"),
    spaceId: spaceId,
    spaceName: space ? space.name : "유휴공간",
    userName: document.getElementById("apply-user-name").value,
    phone: document.getElementById("apply-user-phone").value,
    purpose: document.getElementById("apply-purpose").value,
    purposeName: document.getElementById("apply-purpose").options[document.getElementById("apply-purpose").selectedIndex].text,
    plan: document.getElementById("apply-plan").value,
    period: document.getElementById("apply-period").value,
    teamSize: document.getElementById("apply-team-size").value,
    status: "PENDING",
    statusName: "신청 완료 (심사 대기)",
    appliedAt: new Date().toISOString().split("T")[0]
  };

  appState.applications.unshift(newApp);
  saveData(STORAGE_KEYS.APPLICATIONS);

  closeModal("modal-space-application");
  showToast(`[${newApp.id}] 공간 입주 매칭 신청서가 정식 접수되었습니다!`, "success");
  renderAdminTables();
  updateMetrics();
}

// =============================================================================
// 12. Admin / Provider Portal (ADMIN-SPACE, ADMIN-MATCH, DATA ETL)
// =============================================================================

function switchAdminTab(tab) {
  appState.currentAdminTab = tab;
  document.querySelectorAll(".admin-tab-btn").forEach(b => b.classList.remove("active"));
  event.currentTarget.classList.add("active");

  document.querySelectorAll(".admin-tab-content").forEach(c => c.classList.remove("active"));
  const target = document.getElementById(`admin-tab-${tab}`);
  if (target) target.classList.add("active");
}

function renderAdminTables() {
  // Update badges
  document.getElementById("admin-space-count").textContent = appState.spaces.length;
  document.getElementById("admin-app-count").textContent = appState.applications.length;
  document.getElementById("admin-visit-count").textContent = appState.visits.length;

  // 1. Spaces Table
  const spaceTbody = document.getElementById("admin-spaces-tbody");
  if (spaceTbody) {
    spaceTbody.innerHTML = appState.spaces.map(s => `
      <tr>
        <td><strong>${s.id}</strong></td>
        <td>
          <div style="font-weight:700;">${s.name}</div>
          <div style="font-size:0.75rem; color:var(--text-muted);">${s.address}</div>
        </td>
        <td><span class="card-badge badge-cat">${s.categoryName}</span></td>
        <td>${s.area}㎡ / <strong>월 ${s.monthlyRent}만</strong></td>
        <td>
          <select onchange="updateSpaceStatus('${s.id}', this.value)" style="background:var(--bg-glass); border:1px solid var(--border-glass); border-radius:4px; padding:4px 8px; font-size:0.8rem;">
            <option value="AVAILABLE" ${s.status === 'AVAILABLE' ? 'selected' : ''}>이용 가능</option>
            <option value="RESERVED" ${s.status === 'RESERVED' ? 'selected' : ''}>예약 중</option>
            <option value="IN_USE" ${s.status === 'IN_USE' ? 'selected' : ''}>이용 중</option>
            <option value="REMODELING" ${s.status === 'REMODELING' ? 'selected' : ''}>리모델링 중</option>
            <option value="UNAVAILABLE" ${s.status === 'UNAVAILABLE' ? 'selected' : ''}>이용 불가</option>
          </select>
        </td>
        <td><span style="font-size:0.8rem; color:#818CF8;">${s.remodelingStatus === 'SUPPORT_ELIGIBLE' ? '보조금 지원' : '일반'}</span></td>
        <td>
          <button class="btn-outline" style="padding:4px 8px; font-size:0.75rem;" onclick="deleteSpace('${s.id}')">
            <i class="fa-solid fa-trash" style="color:#EF4444;"></i> 삭제
          </button>
        </td>
      </tr>
    `).join("");
  }

  // 2. Applications Table
  const appsTbody = document.getElementById("admin-apps-tbody");
  if (appsTbody) {
    appsTbody.innerHTML = appState.applications.map(a => `
      <tr>
        <td><strong>${a.id}</strong></td>
        <td>
          <div style="font-weight:700;">${a.userName}</div>
          <div style="font-size:0.75rem; color:var(--text-muted);">${a.phone}</div>
        </td>
        <td><strong>${a.spaceName}</strong></td>
        <td style="max-width:280px; font-size:0.82rem;">
          <div style="color:var(--primary); font-weight:600;">[${a.purposeName}]</div>
          <div style="color:var(--text-muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${a.plan}</div>
        </td>
        <td>${a.appliedAt}</td>
        <td>
          <span class="badge-status ${a.status === 'APPROVED' ? 'badge-success' : (a.status === 'REJECTED' ? 'badge-danger' : 'badge-warning')}">
            ${a.statusName}
          </span>
        </td>
        <td>
          ${a.status === 'PENDING' || a.status === 'REVIEWING' ? `
            <div style="display:flex; gap:4px;">
              <button class="btn-primary" style="padding:4px 8px; font-size:0.75rem;" onclick="approveApplication('${a.id}')">승인</button>
              <button class="btn-outline" style="padding:4px 8px; font-size:0.75rem; color:#EF4444;" onclick="rejectApplication('${a.id}')">거절</button>
            </div>
          ` : `<span style="font-size:0.75rem; color:var(--text-dim);">처리 완료</span>`}
        </td>
      </tr>
    `).join("");
  }

  // 3. Visits Table
  const visitsTbody = document.getElementById("admin-visits-tbody");
  if (visitsTbody) {
    visitsTbody.innerHTML = appState.visits.map(v => `
      <tr>
        <td><strong>${v.id}</strong></td>
        <td>
          <div style="font-weight:700;">${v.userName}</div>
          <div style="font-size:0.75rem; color:var(--text-muted);">${v.phone}</div>
        </td>
        <td>${v.spaceName}</td>
        <td><strong>${v.date} ${v.time}</strong></td>
        <td style="font-size:0.82rem; color:var(--text-muted); max-width:200px;">${v.message}</td>
        <td>
          <span class="badge-status ${v.status === 'APPROVED' ? 'badge-success' : 'badge-warning'}">
            ${v.statusName}
          </span>
        </td>
        <td>
          ${v.status === 'PENDING' ? `
            <button class="btn-primary" style="padding:4px 8px; font-size:0.75rem;" onclick="approveVisit('${v.id}')">일정 승인</button>
          ` : `<span style="font-size:0.75rem; color:var(--text-dim);">승인 완료</span>`}
        </td>
      </tr>
    `).join("");
  }
}

function updateSpaceStatus(spaceId, newStatus) {
  const space = appState.spaces.find(s => s.id === spaceId);
  if (!space) return;

  space.status = newStatus;
  const statusObj = COMMON_CODES.STATUSES.find(st => st.code === newStatus);
  space.statusName = statusObj ? statusObj.name : newStatus;

  saveData(STORAGE_KEYS.SPACES);
  showToast(`[${space.name}] 상태가 '${space.statusName}'(으)로 변경되었습니다.`, "success");
  applyFilters();
}

function deleteSpace(spaceId) {
  if (!confirm("정말 이 유휴공간을 플랫폼에서 비활성화/삭제하시겠습니까?")) return;

  appState.spaces = appState.spaces.filter(s => s.id !== spaceId);
  appState.favorites.delete(spaceId);
  appState.compareList.delete(spaceId);

  saveData(STORAGE_KEYS.SPACES);
  saveData(STORAGE_KEYS.FAVORITES);

  showToast("공간이 삭제되었습니다.", "info");
  renderAdminTables();
  applyFilters();
  updateMetrics();
}

function approveApplication(appId) {
  const app = appState.applications.find(a => a.id === appId);
  if (!app) return;

  app.status = "APPROVED";
  app.statusName = "승인 완료 (계약 진행)";
  saveData(STORAGE_KEYS.APPLICATIONS);

  showToast(`[${appId}] 신청이 승인되었습니다. 입주 계약 절차를 안내합니다.`, "success");
  renderAdminTables();
}

function rejectApplication(appId) {
  const app = appState.applications.find(a => a.id === appId);
  if (!app) return;

  app.status = "REJECTED";
  app.statusName = "반려됨";
  saveData(STORAGE_KEYS.APPLICATIONS);

  showToast(`[${appId}] 신청이 반려되었습니다.`, "warning");
  renderAdminTables();
}

function approveVisit(visitId) {
  const visit = appState.visits.find(v => v.id === visitId);
  if (!visit) return;

  visit.status = "APPROVED";
  visit.statusName = "방문 승인 완료";
  saveData(STORAGE_KEYS.VISITS);

  showToast(`[${visitId}] 방문 신청 일정이 승인되었습니다.`, "success");
  renderAdminTables();
}

function openSpaceRegisterModal() {
  openModal("modal-space-register");
}

function submitSpaceRegister(e) {
  e.preventDefault();

  const newId = "SPC-" + String(appState.spaces.length + 1).padStart(3, "0");
  const district = document.getElementById("reg-district").value;
  const category = document.getElementById("reg-category").value;
  const catObj = COMMON_CODES.CATEGORIES.find(c => c.code === category);

  // Daegu District Approximate Coordinates
  const districtCoords = {
    "중구": [35.8698, 128.5962],
    "동구": [35.8812, 128.6251],
    "서구": [35.8712, 128.5587],
    "남구": [35.8532, 128.5831],
    "북구": [35.8925, 128.6189],
    "수성구": [35.8450, 128.6320],
    "달서구": [35.8384, 128.5492],
    "달성군": [35.8589, 128.4612],
    "군위군": [36.2415, 128.5721]
  };

  const coords = districtCoords[district] || [35.8714, 128.6014];

  const newSpace = {
    id: newId,
    name: document.getElementById("reg-name").value,
    category: category,
    categoryName: catObj ? catObj.name : "일반",
    district: district,
    address: document.getElementById("reg-address").value,
    lat: coords[0] + (Math.random() - 0.5) * 0.01,
    lng: coords[1] + (Math.random() - 0.5) * 0.01,
    area: parseFloat(document.getElementById("reg-area").value),
    pyeong: Math.round(parseFloat(document.getElementById("reg-area").value) / 3.3 * 10) / 10,
    deposit: 300,
    monthlyRent: parseInt(document.getElementById("reg-rent").value),
    maintenanceFee: 5,
    status: "AVAILABLE",
    statusName: "이용 가능",
    remodelingStatus: "SUPPORT_ELIGIBLE",
    remodelingSupport: document.getElementById("reg-support").value || "대구시 리모델링 지원 대상",
    managingAgency: "대구광역시 및 소유자",
    agencyContact: "053-803-0000",
    photos: [
      "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1000&q=80",
      "https://images.unsplash.com/photo-1513694203232-719a280e022f?auto=format&fit=crop&w=1000&q=80"
    ],
    floor: "지상 1층",
    structure: "철근 콘크리트",
    parking: true,
    parkingSpaces: 2,
    utilities: ["수도", "전기", "인터넷", "개별 화장실"],
    transportInfo: "대구 지하철 및 버스정류장 인접",
    tags: ["신규 등록", "도시재생", "청년 환영"],
    description: document.getElementById("reg-desc").value || "대구시 유휴시설 활성화 신규 등록 공간입니다.",
    features: ["초기 입주자 임대료 감면 혜택"],
    createdAt: new Date().toISOString().split("T")[0],
    views: 1,
    favoriteCount: 0
  };

  appState.spaces.unshift(newSpace);
  saveData(STORAGE_KEYS.SPACES);

  closeModal("modal-space-register");
  showToast(`[${newSpace.id}] 신규 유휴공간이 성공적으로 등록 및 공개되었습니다!`, "success");
  applyFilters();
  renderAdminTables();
  updateMetrics();
}

// =============================================================================
// 13. Public Data ETL Pipeline Simulation (DATA-01~04, FR-080~084)
// =============================================================================

function runDataSyncPipeline() {
  const btn = document.getElementById("btn-run-etl");
  const terminal = document.getElementById("etl-terminal-log");
  if (!btn || !terminal) return;

  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> 데이터 수집 및 정제 처리 중...`;

  const logs = [
    `[${new Date().toLocaleTimeString()}] [DATA-01] 대구광역시 공공데이터 API 서버 인증 및 Handshake 완료`,
    `[${new Date().toLocaleTimeString()}] [DATA-01] 공유재산/폐교/빈집 실태조사 OpenAPI 페이징 수집 시작 (총 120 레코드 반환)`,
    `[${new Date().toLocaleTimeString()}] [DATA-02] 네이버/직방 대구 상가 공실 웹 크롤링 서브에이전트 기동 (18개 신규 필지 탐색)`,
    `[${new Date().toLocaleTimeString()}] [DATA-03] 데이터 클렌징 엔진: 좌표 결측치 지오코딩 및 중복 필지 8건 자동 병합`,
    `[${new Date().toLocaleTimeString()}] [DATA-04] PostgreSQL / SQLAlchemy ORM 공간 DB 트랜잭션 커밋 완료 (Success 100%)`
  ];

  let step = 0;
  terminal.innerHTML = "";

  const interval = setInterval(() => {
    if (step < logs.length) {
      terminal.innerHTML += logs[step] + "<br>";
      terminal.scrollTop = terminal.scrollHeight;
      step++;
    } else {
      clearInterval(interval);
      btn.disabled = false;
      btn.innerHTML = `<i class="fa-solid fa-arrows-rotate"></i> 지금 데이터 수집 & 정제 실행`;

      const nowStr = new Date().toISOString().replace("T", " ").slice(0, 16);
      document.getElementById("last-sync-time").textContent = nowStr;
      document.getElementById("total-synced-count").textContent = "138 건";

      showToast("대구 공공데이터 및 크롤링 데이터가 최신 상태로 동기화되었습니다!", "success");
    }
  }, 450);
}

// =============================================================================
// 14. Metrics & Helper Utilities
// =============================================================================

function updateMetrics() {
  const total = appState.spaces.length;
  const avail = appState.spaces.filter(s => s.status === "AVAILABLE").length;
  const totalMatches = appState.applications.length + appState.visits.length;

  document.getElementById("metric-total-spaces").textContent = total;
  document.getElementById("metric-avail-spaces").textContent = avail;
  document.getElementById("metric-match-count").textContent = totalMatches;
}

function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add("active");
  document.body.style.overflow = "hidden";
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove("active");
  document.body.style.overflow = "";
}

// Close modal when clicking on overlay background
document.addEventListener("click", (e) => {
  if (e.target.classList.contains("modal-overlay")) {
    e.target.classList.remove("active");
    document.body.style.overflow = "";
  }
});

function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;

  const iconClass = type === "success" ? "fa-circle-check" : (type === "warning" ? "fa-triangle-exclamation" : "fa-circle-info");
  toast.innerHTML = `<i class="fa-solid ${iconClass}"></i> <span>${message}</span>`;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}
