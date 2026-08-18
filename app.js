/* 다시, 공간 — Project 2 interaction layer */

const STORAGE = {
  favorites: 'dasi-space-v2-favorites',
  spaces: 'dasi-space-v2-spaces',
  applications: 'dasi-space-v2-applications'
};

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
  map: null,
  markers: []
};

document.addEventListener('DOMContentLoaded', init);

function init() {
  loadState();
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

function loadState() {
  appState.spaces = readStorage(STORAGE.spaces, INITIAL_SPACES).map(function (space) {
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

  if (!appState.filteredSpaces.length) {
    container.innerHTML = '<div class="empty-state"><strong>조건에 맞는 공간이 없어요.</strong><span>범위를 조금 넓혀 다시 찾아보세요.</span><br><button type="button" data-action="reset-filters">조건 초기화</button></div>';
  } else {
    container.innerHTML = appState.filteredSpaces.map(createCard).join('');
  }

  updateFavoriteCount();
  updateMapMarkers(appState.filteredSpaces);
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
        '<div class="card-specs"><span>' + formatArea(space.area) + '</span><span>' + formatRent(space.monthlyRent) + '</span><span>' + (space.parking ? '주차 ' + space.parkingSpaces + '대' : '주차 불가') + '</span></div>',
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

    if (districtTarget) {
      appState.filters.district = districtTarget.dataset.district;
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
    renderCatalog();
  });

  document.getElementById('searchSubmit').addEventListener('click', renderCatalog);
  document.getElementById('categoryFilter').addEventListener('change', applyControlFilters);
  document.getElementById('rentFilter').addEventListener('change', applyControlFilters);
  document.getElementById('areaFilter').addEventListener('change', applyControlFilters);
  document.getElementById('parkingFilter').addEventListener('change', applyControlFilters);
  document.getElementById('sortSelect').addEventListener('change', function () {
    appState.filters.sort = this.value;
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
      '<div class="detail-photo"><img src="' + space.photos[0] + '" alt="' + space.name + '"></div>',
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
      '<div><h3>시설 정보</h3><ul class="utility-list">' + space.utilities.map(function (item) { return '<li>' + item + '</li>'; }).join('') + '</ul><div class="support-box"><strong>리모델링·지원 정책</strong><p>' + space.remodelingSupport + '</p></div><p><strong>관리 기관</strong><br>' + space.managingAgency + '<br>' + space.agencyContact + '</p></div>',
    '</div>'
  ].join('');
  openModal('detailModal');
}

function openApplication(id) {
  const space = findSpace(id);
  if (!space) return;
  closeModal(document.getElementById('detailModal'));
  document.getElementById('applySpaceId').value = id;
  document.getElementById('applySpaceName').textContent = space.name;
  openModal('applyModal');
}

function submitApplication(event) {
  event.preventDefault();
  const id = document.getElementById('applySpaceId').value;
  appState.applications.unshift({
    id: 'APP-' + Date.now(),
    spaceId: id,
    name: document.getElementById('applicantName').value.trim(),
    phone: document.getElementById('applicantPhone').value.trim(),
    visitDate: document.getElementById('visitDate').value,
    message: document.getElementById('applyMessage').value.trim(),
    status: 'PENDING',
    createdAt: new Date().toISOString()
  });
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
  return rent === 0 ? '사용료 무료' : '월 ' + Number(rent).toLocaleString('ko-KR') + '만원';
}

function formatMoney(amount) {
  return amount === 0 ? '없음' : Number(amount).toLocaleString('ko-KR') + '만원';
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
