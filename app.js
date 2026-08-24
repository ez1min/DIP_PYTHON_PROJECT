/* 다시, 공간 — Project 2 interaction layer */

const STORAGE = {
  favorites: 'dasi-space-v2-favorites',
  spaces: 'dasi-space-v2-spaces',
  applications: 'dasi-space-v2-applications'
};

const PAGE_SIZE = 9;

const appState = {
  spaces: [],
  favorites: new Set(),
  applications: [],
  filters: {
    query: '',
    district: 'ALL',
    category: 'ALL',
    maxRent: 999,
    minArea: 0,
    parking: false,
    sort: 'recommended'
  },
  filteredSpaces: [],
  page: 1,
  map: null,
  markers: []
};

document.addEventListener('DOMContentLoaded', function () {
  init().catch(function (error) {
    console.error('초기화 실패', error);
  });
});

async function init() {
  await loadState();
  populateOptions();
  renderDistrictChips();
  renderFeatured();
  renderCatalog();
  renderDistrictStats();
  renderFavorites();
  bindEvents();
  initMap();
  setMinimumVisitDate();
}

// FastAPI 백엔드가 없거나(정적 서버로만 띄운 경우) 응답이 실패하면
// data.js에 번들된 INITIAL_SPACES/COMMON_CODES로 조용히 대체한다.
async function fetchJSON(path) {
  const response = await fetch(path, { headers: { Accept: 'application/json' } });
  if (!response.ok) throw new Error(path + ' -> HTTP ' + response.status);
  return response.json();
}

async function loadState() {
  let apiSpaces = null;
  try {
    apiSpaces = await fetchJSON('/api/v1/spaces');
  } catch (error) {
    console.warn('공간 데이터를 API에서 불러오지 못해 번들 데이터를 씁니다.', error);
  }

  try {
    const codes = await fetchJSON('/api/v1/common-codes');
    COMMON_CODES.USER_TYPES = codes.userTypes;
    COMMON_CODES.CATEGORIES = codes.categories;
    COMMON_CODES.DISTRICTS = codes.districts;
    COMMON_CODES.STATUSES = codes.statuses;
  } catch (error) {
    console.warn('공통 코드를 API에서 불러오지 못해 번들 데이터를 씁니다.', error);
  }

  // localStorage에 저장된 값(운영센터에서 변경한 상태 등)이 있으면 그것을 우선한다.
  // 첫 방문이라 저장된 값이 없을 때만 API 결과(없으면 번들 데이터)를 기본값으로 쓴다.
  appState.spaces = readStorage(STORAGE.spaces, apiSpaces || INITIAL_SPACES).map(function (space) {
    return Object.assign({}, space);
  });
  appState.favorites = new Set(readStorage(STORAGE.favorites, []));
  appState.applications = readStorage(STORAGE.applications, []);
}

function readStorage(key, fallback) {
  try {
    const saved = localStorage.getItem(key);
    return saved ? JSON.parse(saved) : fallback;
  } catch (error) {
    console.warn('저장 데이터를 읽지 못했습니다.', error);
    return fallback;
  }
}

function saveState(key) {
  if (key === STORAGE.favorites) {
    localStorage.setItem(key, JSON.stringify(Array.from(appState.favorites)));
  }
  if (key === STORAGE.spaces) {
    localStorage.setItem(key, JSON.stringify(appState.spaces));
  }
  if (key === STORAGE.applications) {
    localStorage.setItem(key, JSON.stringify(appState.applications));
  }
}

function populateOptions() {
  const categoryFilter = document.getElementById('categoryFilter');
  const recommendPurpose = document.getElementById('recommendPurpose');
  const recommendDistrict = document.getElementById('recommendDistrict');

  COMMON_CODES.CATEGORIES.forEach(function (category) {
    categoryFilter.insertAdjacentHTML('beforeend', '<option value="' + category.code + '">' + category.name + '</option>');
    recommendPurpose.insertAdjacentHTML('beforeend', '<option value="' + category.code + '">' + category.name + '</option>');
  });

  COMMON_CODES.DISTRICTS.forEach(function (district) {
    recommendDistrict.insertAdjacentHTML('beforeend', '<option value="' + district + '">' + district + '</option>');
  });
}

function renderDistrictChips() {
  const container = document.getElementById('districtChips');
  const districts = ['ALL'].concat(COMMON_CODES.DISTRICTS);
  container.innerHTML = districts.map(function (district) {
    const label = district === 'ALL' ? '대구 전체' : district;
    const active = appState.filters.district === district ? ' active' : '';
    return '<button class="district-chip' + active + '" type="button" data-district="' + district + '">' + label + '</button>';
  }).join('');
}

function renderFeatured() {
  const featured = appState.spaces.find(function (space) { return space.id === 'SPC-001'; }) || appState.spaces[0];
  if (!featured) return;

  document.getElementById('featuredImage').src = featured.photos[0];
  document.getElementById('featuredImage').alt = featured.name;
  document.getElementById('featuredName').textContent = featured.name;
  document.getElementById('featuredDistrict').textContent = featured.district;
  document.getElementById('featuredArea').textContent = formatArea(featured.area);
  document.getElementById('featuredRent').textContent = formatRent(featured.monthlyRent);
  document.getElementById('heroSpaceCount').textContent = appState.spaces.length;

  const favoriteButton = document.querySelector('[data-featured-favorite]');
  favoriteButton.dataset.spaceId = featured.id;
  favoriteButton.textContent = appState.favorites.has(featured.id) ? '♥' : '♡';
  favoriteButton.classList.toggle('active', appState.favorites.has(featured.id));
}

function getFilteredSpaces() {
  const filter = appState.filters;
  let spaces = appState.spaces.filter(function (space) {
    const searchable = [
      space.name,
      space.address,
      space.district,
      space.categoryName,
      space.description
    ].concat(space.tags || []).join(' ').toLowerCase();

    return (!filter.query || searchable.includes(filter.query.toLowerCase()))
      && (filter.district === 'ALL' || space.district === filter.district)
      && (filter.category === 'ALL' || space.category === filter.category)
      && space.monthlyRent <= filter.maxRent
      && space.area >= filter.minArea
      && (!filter.parking || space.parking);
  });

  if (filter.sort === 'rent-low') {
    spaces.sort(function (a, b) { return a.monthlyRent - b.monthlyRent; });
  } else if (filter.sort === 'area-large') {
    spaces.sort(function (a, b) { return b.area - a.area; });
  } else if (filter.sort === 'popular') {
    spaces.sort(function (a, b) { return (b.favoriteCount + b.views) - (a.favoriteCount + a.views); });
  } else {
    spaces.sort(function (a, b) {
      const availableA = a.status === 'AVAILABLE' ? 1 : 0;
      const availableB = b.status === 'AVAILABLE' ? 1 : 0;
      return availableB - availableA || b.favoriteCount - a.favoriteCount;
    });
  }

  return spaces;
}

function renderCatalog() {
  appState.filteredSpaces = getFilteredSpaces();
  const container = document.getElementById('spaceGrid');
  document.getElementById('resultCount').textContent = appState.filteredSpaces.length;
  document.getElementById('mapSpaceCount').textContent = appState.filteredSpaces.length + '곳';

  const totalPages = Math.max(1, Math.ceil(appState.filteredSpaces.length / PAGE_SIZE));
  // 필터가 바뀌어 결과가 줄면 이전 페이지 번호가 범위를 벗어날 수 있다.
  if (appState.page > totalPages) appState.page = totalPages;
  if (appState.page < 1) appState.page = 1;

  if (!appState.filteredSpaces.length) {
    container.innerHTML = '<div class="empty-state"><strong>조건에 맞는 공간이 없어요.</strong><span>범위를 조금 넓혀 다시 찾아보세요.</span><br><button type="button" data-action="reset-filters">조건 초기화</button></div>';
  } else {
    const start = (appState.page - 1) * PAGE_SIZE;
    const pageSpaces = appState.filteredSpaces.slice(start, start + PAGE_SIZE);
    container.innerHTML = pageSpaces.map(createCard).join('');
  }

  renderPagination(totalPages);
  updateFavoriteCount();
  updateMapMarkers(appState.filteredSpaces);
}

function renderPagination(totalPages) {
  const nav = document.getElementById('spacePagination');
  if (!nav) return;
  if (totalPages <= 1) {
    nav.innerHTML = '';
    return;
  }

  const current = appState.page;
  const pageNumberButton = function (page) {
    return '<button type="button" data-page="' + page + '"' + (page === current ? ' class="active" aria-current="page"' : '') + '>' + page + '</button>';
  };
  const ellipsis = '<span class="pagination-ellipsis">…</span>';

  // 페이지가 많아지면 앞/뒤/현재 주변만 보여주고 나머지는 …으로 줄인다.
  const pages = [];
  for (let page = 1; page <= totalPages; page++) {
    if (page === 1 || page === totalPages || Math.abs(page - current) <= 1) {
      pages.push(pageNumberButton(page));
    } else if (pages[pages.length - 1] !== ellipsis) {
      pages.push(ellipsis);
    }
  }

  nav.innerHTML =
    '<button type="button" data-page="' + (current - 1) + '" ' + (current === 1 ? 'disabled' : '') + ' aria-label="이전 페이지">‹</button>' +
    pages.join('') +
    '<button type="button" data-page="' + (current + 1) + '" ' + (current === totalPages ? 'disabled' : '') + ' aria-label="다음 페이지">›</button>';
}

function goToPage(page) {
  const totalPages = Math.max(1, Math.ceil(appState.filteredSpaces.length / PAGE_SIZE));
  page = Math.min(Math.max(1, page), totalPages);
  if (page === appState.page) return;
  appState.page = page;
  renderCatalog();
  document.getElementById('spaceGrid').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function createCard(space) {
  const saved = appState.favorites.has(space.id);
  const ribbonClass = space.status === 'AVAILABLE' ? '' : ' reserved';
  return [
    '<article class="space-card">',
      '<div class="card-image">',
        '<img src="' + space.photos[0] + '" alt="' + space.name + '" loading="lazy">',
        '<span class="status-ribbon' + ribbonClass + '">' + getStatusName(space.status) + '</span>',
        '<button class="card-favorite' + (saved ? ' active' : '') + '" type="button" data-action="favorite" data-space-id="' + space.id + '" aria-label="관심 공간 저장">' + (saved ? '♥' : '♡') + '</button>',
      '</div>',
      '<div class="card-body">',
        '<div class="card-category"><span>' + categorySymbol(space.category) + ' ' + space.categoryName.toUpperCase() + '</span><span>' + space.district + '</span></div>',
        '<h3>' + space.name + '</h3>',
        '<p class="card-address">' + space.address + '</p>',
        '<div class="card-specs"><span>' + formatArea(space.area) + '</span><span>' + formatRent(space.monthlyRent) + '</span><span>' + (space.parking ? '주차 ' + space.parkingSpaces + '대' : '주차 불가') + '</span>' +
          (space.lastTransaction ? '<span>실거래 ' + formatTransactionSummary(space.lastTransaction) + '</span>' : '') +
        '</div>',
        '<div class="card-actions">',
          '<button type="button" data-action="detail" data-space-id="' + space.id + '">공간 자세히 보기</button>',
          '<button type="button" data-action="detail" data-space-id="' + space.id + '" aria-label="상세 보기">↗</button>',
        '</div>',
      '</div>',
    '</article>'
  ].join('');
}

function renderDistrictStats() {
  const counts = {};
  appState.spaces.forEach(function (space) {
    counts[space.district] = (counts[space.district] || 0) + 1;
  });
  document.getElementById('districtStats').innerHTML = COMMON_CODES.DISTRICTS.slice(0, 6).map(function (district) {
    return '<div class="district-stat"><span>' + district + '</span><strong>' + (counts[district] || 0) + ' spaces</strong></div>';
  }).join('');
}

function bindEvents() {
  document.addEventListener('click', function (event) {
    const actionTarget = event.target.closest('[data-action]');
    const districtTarget = event.target.closest('[data-district]');
    const modalClose = event.target.closest('[data-close-modal]');
    const pageTarget = event.target.closest('[data-page]');

    if (pageTarget) {
      goToPage(Number(pageTarget.dataset.page));
      return;
    }

    if (districtTarget) {
      appState.filters.district = districtTarget.dataset.district;
      appState.page = 1;
      renderDistrictChips();
      renderCatalog();
      return;
    }

    if (modalClose) {
      closeModal(modalClose.closest('.modal'));
      return;
    }

    if (!actionTarget) return;
    handleAction(actionTarget.dataset.action, actionTarget);
  });

  document.getElementById('featuredName').closest('.featured-card').addEventListener('click', function (event) {
    if (event.target.closest('button')) return;
    const id = document.querySelector('[data-featured-favorite]').dataset.spaceId;
    openDetail(id);
  });

  document.querySelector('[data-featured-favorite]').addEventListener('click', function () {
    toggleFavorite(this.dataset.spaceId);
  });

  document.getElementById('searchInput').addEventListener('input', function () {
    appState.filters.query = this.value.trim();
    appState.page = 1;
    renderCatalog();
  });

  document.getElementById('searchSubmit').addEventListener('click', function () {
    appState.page = 1;
    renderCatalog();
  });
  document.getElementById('categoryFilter').addEventListener('change', applyControlFilters);
  document.getElementById('rentFilter').addEventListener('change', applyControlFilters);
  document.getElementById('areaFilter').addEventListener('change', applyControlFilters);
  document.getElementById('parkingFilter').addEventListener('change', applyControlFilters);
  document.getElementById('sortSelect').addEventListener('change', function () {
    appState.filters.sort = this.value;
    appState.page = 1;
    renderCatalog();
  });

  document.getElementById('filterToggle').addEventListener('click', toggleFilterPanel);
  document.getElementById('resetFilters').addEventListener('click', resetFilters);
  document.getElementById('drawerBackdrop').addEventListener('click', closeFavorites);
  document.getElementById('recommendForm').addEventListener('submit', submitRecommendation);
  document.getElementById('applyForm').addEventListener('submit', submitApplication);
  document.getElementById('syncData').addEventListener('click', simulateDataSync);

  document.getElementById('adminSpaceRows').addEventListener('change', function (event) {
    if (!event.target.matches('[data-status-space]')) return;
    updateSpaceStatus(event.target.dataset.statusSpace, event.target.value);
  });

  document.querySelectorAll('.modal').forEach(function (modal) {
    modal.addEventListener('click', function (event) {
      if (event.target === modal) closeModal(modal);
    });
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') {
      document.querySelectorAll('.modal.open').forEach(closeModal);
      closeFavorites();
    }
  });
}

function handleAction(action, element) {
  const id = element.dataset.spaceId;
  const actions = {
    'favorite': function () { toggleFavorite(id); },
    'detail': function () { openDetail(id); },
    'apply': function () { openApplication(id); },
    'open-favorites': openFavorites,
    'close-favorites': closeFavorites,
    'open-recommend': function () { openModal('recommendModal'); },
    'open-admin': openAdmin,
    'show-map': showMap,
    'scroll-discover': function () { scrollToId('discover'); },
    'reset-filters': resetFilters
  };
  if (actions[action]) actions[action]();
}

function applyControlFilters() {
  appState.filters.category = document.getElementById('categoryFilter').value;
  appState.filters.maxRent = Number(document.getElementById('rentFilter').value);
  appState.filters.minArea = Number(document.getElementById('areaFilter').value);
  appState.filters.parking = document.getElementById('parkingFilter').checked;
  appState.page = 1;
  renderCatalog();
}

function toggleFilterPanel() {
  const panel = document.getElementById('filterPanel');
  const button = document.getElementById('filterToggle');
  const open = panel.classList.toggle('open');
  panel.setAttribute('aria-hidden', String(!open));
  button.setAttribute('aria-expanded', String(open));
  button.querySelector('span').textContent = open ? '−' : '＋';
}

function resetFilters() {
  appState.filters = {
    query: '',
    district: 'ALL',
    category: 'ALL',
    maxRent: 999,
    minArea: 0,
    parking: false,
    sort: 'recommended'
  };
  document.getElementById('searchInput').value = '';
  document.getElementById('categoryFilter').value = 'ALL';
  document.getElementById('rentFilter').value = '999';
  document.getElementById('areaFilter').value = '0';
  document.getElementById('parkingFilter').checked = false;
  document.getElementById('sortSelect').value = 'recommended';
  appState.page = 1;
  renderDistrictChips();
  renderCatalog();
}

function toggleFavorite(id) {
  if (!id) return;
  if (appState.favorites.has(id)) {
    appState.favorites.delete(id);
    toast('저장한 공간에서 제외했습니다.');
  } else {
    appState.favorites.add(id);
    toast('관심 공간으로 저장했습니다.', 'success');
  }
  saveState(STORAGE.favorites);
  renderCatalog();
  renderFeatured();
  renderFavorites();
}

function updateFavoriteCount() {
  document.getElementById('favoriteCount').textContent = appState.favorites.size;
}

function renderFavorites() {
  const list = document.getElementById('favoritesList');
  const favorites = appState.spaces.filter(function (space) { return appState.favorites.has(space.id); });
  updateFavoriteCount();

  if (!favorites.length) {
    list.innerHTML = '<div class="drawer-empty"><strong>아직 저장한 공간이 없어요.</strong><span>마음에 드는 카드의 하트를 눌러보세요.</span></div>';
    return;
  }

  list.innerHTML = favorites.map(function (space) {
    return [
      '<div class="favorite-drawer-item">',
        '<img src="' + space.photos[0] + '" alt="">',
        '<div><h3><a href="#" data-action="detail" data-space-id="' + space.id + '">' + space.name + '</a></h3><p>' + space.district + ' · ' + formatRent(space.monthlyRent) + '</p></div>',
        '<button type="button" data-action="favorite" data-space-id="' + space.id + '" aria-label="삭제">×</button>',
      '</div>'
    ].join('');
  }).join('');
}

function openFavorites() {
  renderFavorites();
  document.getElementById('favoritesDrawer').classList.add('open');
  document.getElementById('favoritesDrawer').setAttribute('aria-hidden', 'false');
  document.getElementById('drawerBackdrop').classList.add('open');
  document.body.classList.add('modal-open');
}

function closeFavorites() {
  document.getElementById('favoritesDrawer').classList.remove('open');
  document.getElementById('favoritesDrawer').setAttribute('aria-hidden', 'true');
  document.getElementById('drawerBackdrop').classList.remove('open');
  if (!document.querySelector('.modal.open')) document.body.classList.remove('modal-open');
}

function openDetail(id) {
  const space = findSpace(id);
  if (!space) return;
  closeFavorites();

  const saved = appState.favorites.has(id);
  document.getElementById('detailContent').innerHTML = [
    '<div class="detail-hero">',
      '<div class="detail-photo" id="detailPhoto"><div id="detailRoadview" style="width:100%;height:100%"></div></div>',
      '<div class="detail-summary">',
        '<span class="category">' + categorySymbol(space.category) + ' ' + space.categoryName.toUpperCase() + ' · ' + getStatusName(space.status) + '</span>',
        '<h2>' + space.name + '</h2>',
        '<p class="address">' + space.address + '<br>' + space.transportInfo + '</p>',
        '<div class="detail-price">',
          '<div><span>전용 면적</span><strong>' + formatArea(space.area) + '</strong></div>',
          '<div><span>보증금</span><strong>' + formatMoney(space.deposit) + '</strong></div>',
          '<div><span>월 임대료</span><strong>' + formatMoney(space.monthlyRent) + '</strong></div>',
        '</div>',
        '<div class="detail-summary-actions">',
          '<button type="button" data-action="apply" data-space-id="' + space.id + '">방문 및 이용 신청 →</button>',
          '<button type="button" data-action="favorite" data-space-id="' + space.id + '">' + (saved ? '♥' : '♡') + '</button>',
        '</div>',
      '</div>',
    '</div>',
    '<div class="detail-body">',
      '<div><h3>공간 이야기</h3><p>' + space.description + '</p><h3>이 공간의 특징</h3><ul class="feature-list">' + space.features.map(function (item) { return '<li>' + item + '</li>'; }).join('') + '</ul></div>',
      '<div><h3>시설 정보</h3><ul class="utility-list">' + space.utilities.map(function (item) { return '<li>' + item + '</li>'; }).join('') + '</ul><div class="support-box"><strong>리모델링·지원 정책</strong><p>' + space.remodelingSupport + '</p></div>' +
        '<div class="support-box"><strong>실거래 정보</strong><p>' + (
          space.lastTransaction
            ? formatTransactionSummary(space.lastTransaction) + ' · ' + space.lastTransaction.dealDate + ' · ' + space.lastTransaction.source
            : '국토부 실거래가에서 확인된 거래가 없습니다(거래 없음 또는 지번 마스킹으로 확인 불가).'
        ) + '</p></div>' +
        '<p><strong>관리 기관</strong><br>' + space.managingAgency + '<br>' + space.agencyContact + '</p></div>',
    '</div>'
  ].join('');
  openModal('detailModal');
  // 모달이 열려 실제 크기를 갖춘 다음 프레임에 로드뷰를 그린다 —
  // 숨겨진(0px) 컨테이너에 바로 그리면 카카오 SDK가 캔버스 크기를 못 잡는다.
  window.requestAnimationFrame(function () {
    renderRoadview(space);
  });
}

let kakaoSdkPromise = null;

// Kakao JS 키는 서버 설정 엔드포인트에서 받아온다 — 정적 파일에 하드코딩하지 않는다.
function loadKakaoSdk() {
  if (kakaoSdkPromise) return kakaoSdkPromise;
  kakaoSdkPromise = fetchJSON('/api/v1/config').then(function (config) {
    if (!config.kakaoJsKey) throw new Error('카카오 JS 키가 설정되지 않았습니다.');
    return new Promise(function (resolve, reject) {
      const script = document.createElement('script');
      script.src = '//dapi.kakao.com/v2/maps/sdk.js?appkey=' + config.kakaoJsKey + '&autoload=false';
      script.onload = function () {
        kakao.maps.load(resolve);
      };
      script.onerror = function () {
        reject(new Error('카카오 지도 SDK 로드 실패'));
      };
      document.head.appendChild(script);
    });
  });
  return kakaoSdkPromise;
}

function showPhotoFallback(container, space, message) {
  container.innerHTML = '<img src="' + space.photos[0] + '" alt="' + space.name + '">' +
    '<span class="roadview-fallback-note">' + message + '</span>';
}

function renderRoadview(space) {
  const container = document.getElementById('detailRoadview');
  if (!container) return; // 그 사이 모달이 닫혔거나 다른 공간으로 바뀜

  loadKakaoSdk().then(function () {
    const roadview = new kakao.maps.Roadview(container);
    const roadviewClient = new kakao.maps.RoadviewClient();
    const position = new kakao.maps.LatLng(space.lat, space.lng);

    roadviewClient.getNearestPanoId(position, 50, function (panoId) {
      if (document.getElementById('detailRoadview') !== container) return; // 이미 다른 공간을 보고 있음
      if (panoId === null) {
        showPhotoFallback(container, space, '이 위치는 로드뷰를 제공하지 않습니다.');
        return;
      }
      roadview.setPanoId(panoId, position);
    });
  }).catch(function (error) {
    console.warn('로드뷰를 불러오지 못했습니다.', error);
    if (document.getElementById('detailRoadview') === container) {
      showPhotoFallback(container, space, '로드뷰를 불러오지 못했습니다.');
    }
  });
}

function openApplication(id) {
  const space = findSpace(id);
  if (!space) return;
  closeModal(document.getElementById('detailModal'));
  document.getElementById('applySpaceId').value = id;
  document.getElementById('applySpaceName').textContent = space.name;
  openModal('applyModal');
}

async function submitApplication(event) {
  event.preventDefault();
  const payload = {
    spaceId: document.getElementById('applySpaceId').value,
    name: document.getElementById('applicantName').value.trim(),
    phone: document.getElementById('applicantPhone').value.trim(),
    visitDate: document.getElementById('visitDate').value,
    message: document.getElementById('applyMessage').value.trim()
  };

  let application = null;
  try {
    const response = await fetch('/api/v1/applications', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (response.ok) application = await response.json();
  } catch (error) {
    console.warn('신청 접수를 서버에 저장하지 못해 이 기기에만 남깁니다.', error);
  }

  appState.applications.unshift(application || Object.assign({
    id: 'APP-' + Date.now(),
    status: 'PENDING',
    createdAt: new Date().toISOString()
  }, payload));
  saveState(STORAGE.applications);
  event.target.reset();
  setMinimumVisitDate();
  closeModal(document.getElementById('applyModal'));
  toast('방문·이용 신청을 접수했습니다.', 'success');
}

function submitRecommendation(event) {
  event.preventDefault();
  const criteria = {
    district: document.getElementById('recommendDistrict').value,
    purpose: document.getElementById('recommendPurpose').value,
    budget: Number(document.getElementById('recommendBudget').value),
    area: Number(document.getElementById('recommendArea').value),
    parking: document.getElementById('recommendParking').checked
  };

  const results = appState.spaces.map(function (space) {
    let score = 15;
    const reasons = [];

    if (criteria.district === 'ALL' || space.district === criteria.district) {
      score += 25;
      reasons.push(criteria.district === 'ALL' ? '대구 전역 조건' : criteria.district + ' 선호 지역');
    }
    if (space.category === criteria.purpose) {
      score += 30;
      reasons.push(space.categoryName + ' 활용 적합');
    }
    if (space.monthlyRent <= criteria.budget) {
      score += 20;
      reasons.push('월 예산 이내');
    } else if (space.monthlyRent <= criteria.budget + 10) {
      score += 8;
    }
    if (space.area >= criteria.area) {
      score += 10;
      reasons.push('면적 조건 충족');
    }
    if (criteria.parking && space.parking) {
      score += 8;
      reasons.push('주차 가능');
    }
    if (!criteria.parking) score += 5;

    return { space: space, score: Math.min(score, 98), reasons: reasons };
  }).sort(function (a, b) { return b.score - a.score; }).slice(0, 3);

  const resultBox = document.getElementById('recommendResults');
  resultBox.hidden = false;
  resultBox.innerHTML = '<h3>가장 잘 맞는 공간이에요.</h3>' + results.map(function (result) {
    return [
      '<div class="recommend-result-item">',
        '<div class="recommend-score">' + result.score + '%</div>',
        '<div><h4>' + result.space.name + '</h4><p>' + (result.reasons.join(' · ') || '조건을 넓혀 발견한 공간') + '</p></div>',
        '<button type="button" data-action="detail" data-space-id="' + result.space.id + '">자세히 보기</button>',
      '</div>'
    ].join('');
  }).join('');
  resultBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function initMap() {
  if (typeof L === 'undefined') {
    document.getElementById('map').innerHTML = '<div class="empty-state">지도를 불러오지 못했습니다. 인터넷 연결을 확인해주세요.</div>';
    return;
  }

  appState.map = L.map('map', {
    center: [35.8714, 128.6014],
    zoom: 11,
    zoomControl: false,
    scrollWheelZoom: false
  });

  L.control.zoom({ position: 'bottomleft' }).addTo(appState.map);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap'
  }).addTo(appState.map);
  updateMapMarkers(appState.filteredSpaces.length ? appState.filteredSpaces : appState.spaces);
}

function updateMapMarkers(spaces) {
  if (!appState.map || typeof L === 'undefined') return;
  appState.markers.forEach(function (marker) { marker.remove(); });
  appState.markers = [];

  spaces.forEach(function (space) {
    const icon = L.divIcon({
      className: '',
      html: '<div class="custom-map-pin"><span>' + space.district.slice(0, 1) + '</span></div>',
      iconSize: [34, 34],
      iconAnchor: [17, 34],
      popupAnchor: [0, -30]
    });

    const popup = '<div class="map-popup"><span>' + space.district + ' · ' + space.categoryName + '</span><strong>' + space.name + '</strong><span>' + formatArea(space.area) + ' · ' + formatRent(space.monthlyRent) + '</span><button type="button" onclick="openDetail(\'' + space.id + '\')">공간 보기</button></div>';
    const marker = L.marker([space.lat, space.lng], { icon: icon }).addTo(appState.map).bindPopup(popup);
    appState.markers.push(marker);
  });

  if (appState.markers.length > 1) {
    const bounds = L.featureGroup(appState.markers).getBounds();
    appState.map.fitBounds(bounds.pad(0.18), { maxZoom: 13 });
  } else if (appState.markers.length === 1) {
    appState.map.setView(appState.markers[0].getLatLng(), 14);
  }
}

function showMap() {
  scrollToId('mapSection');
  window.setTimeout(function () {
    if (appState.map) appState.map.invalidateSize();
  }, 450);
}

function openAdmin() {
  renderAdmin();
  openModal('adminModal');
}

function renderAdmin() {
  const available = appState.spaces.filter(function (space) { return space.status === 'AVAILABLE'; }).length;
  const remodeling = appState.spaces.filter(function (space) { return space.status === 'REMODELING'; }).length;
  document.getElementById('adminMetrics').innerHTML = [
    '<div class="admin-metric"><span>전체 등록 공간</span><strong>' + appState.spaces.length + '</strong></div>',
    '<div class="admin-metric"><span>즉시 이용 가능</span><strong>' + available + '</strong></div>',
    '<div class="admin-metric"><span>리모델링 중</span><strong>' + remodeling + '</strong></div>',
    '<div class="admin-metric"><span>접수 신청</span><strong>' + appState.applications.length + '</strong></div>'
  ].join('');

  document.getElementById('adminSpaceRows').innerHTML = appState.spaces.map(function (space) {
    return [
      '<tr>',
        '<td>' + space.name + '</td>',
        '<td>' + space.district + '</td>',
        '<td>' + formatMoney(space.monthlyRent) + '</td>',
        '<td><select data-status-space="' + space.id + '">' + COMMON_CODES.STATUSES.map(function (status) {
          return '<option value="' + status.code + '"' + (status.code === space.status ? ' selected' : '') + '>' + status.name + '</option>';
        }).join('') + '</select></td>',
      '</tr>'
    ].join('');
  }).join('');
}

function updateSpaceStatus(id, status) {
  const space = findSpace(id);
  if (!space) return;
  space.status = status;
  space.statusName = getStatusName(status);
  saveState(STORAGE.spaces);
  renderCatalog();
  renderFeatured();
  renderAdmin();
  toast('공간 상태를 ' + getStatusName(status) + '(으)로 변경했습니다.', 'success');
}

function simulateDataSync() {
  const button = document.getElementById('syncData');
  button.disabled = true;
  button.textContent = '데이터 확인 중…';
  window.setTimeout(function () {
    button.disabled = false;
    button.textContent = '공공데이터 동기화 ↻';
    toast('대구시 공공데이터 60건을 확인했습니다.', 'success');
  }, 1200);
}

function openModal(id) {
  const modal = typeof id === 'string' ? document.getElementById(id) : id;
  if (!modal) return;
  modal.classList.add('open');
  modal.setAttribute('aria-hidden', 'false');
  document.body.classList.add('modal-open');
}

function closeModal(modal) {
  if (!modal) return;
  modal.classList.remove('open');
  modal.setAttribute('aria-hidden', 'true');
  if (!document.querySelector('.modal.open') && !document.getElementById('favoritesDrawer').classList.contains('open')) {
    document.body.classList.remove('modal-open');
  }
}

function scrollToId(id) {
  const target = document.getElementById(id);
  if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function setMinimumVisitDate() {
  const input = document.getElementById('visitDate');
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  input.min = tomorrow.toISOString().slice(0, 10);
}

function findSpace(id) {
  return appState.spaces.find(function (space) { return space.id === id; });
}

function getStatusName(code) {
  const status = COMMON_CODES.STATUSES.find(function (item) { return item.code === code; });
  return status ? status.name : code;
}

function categorySymbol(code) {
  const symbols = {
    STARTUP: '↗',
    SHOP: '◆',
    OFFICE: '▣',
    ART: '●',
    WORKSHOP: '▲',
    SOCIAL: '♥'
  };
  return symbols[code] || '■';
}

function formatArea(area) {
  return Number(area).toLocaleString('ko-KR') + '㎡';
}

function formatRent(rent) {
  // 0은 "무료"가 아니라 공공데이터 파이프라인이 채우지 못한 "정보 없음"일 수 있다.
  return rent === 0 ? '임대료 정보 없음' : '월 ' + Number(rent).toLocaleString('ko-KR') + '만원';
}

function formatMoney(amount) {
  return amount === 0 ? '없음' : Number(amount).toLocaleString('ko-KR') + '만원';
}

const DEAL_TYPE_LABELS = {
  SALE: '매매',
  JEONSE: '전세',
  MONTHLY_RENT: '월세'
};

function dealTypeLabel(dealType) {
  return DEAL_TYPE_LABELS[dealType] || dealType;
}

function formatTransactionSummary(transaction) {
  if (!transaction) return '';
  let text = dealTypeLabel(transaction.dealType) + ' ' + Number(transaction.dealAmount).toLocaleString('ko-KR') + '만원';
  if (transaction.dealType === 'MONTHLY_RENT' && transaction.monthlyRent != null) {
    text += ' / 월 ' + Number(transaction.monthlyRent).toLocaleString('ko-KR') + '만원';
  }
  return text;
}

function toast(message, type) {
  const region = document.getElementById('toastRegion');
  const element = document.createElement('div');
  element.className = 'toast' + (type ? ' ' + type : '');
  element.textContent = message;
  region.appendChild(element);
  window.setTimeout(function () {
    element.style.opacity = '0';
    element.style.transform = 'translateY(8px)';
    window.setTimeout(function () { element.remove(); }, 250);
  }, 2800);
}
