// 성능 최적화 스크립트

// 페이지 로딩 시간 측정
document.addEventListener('DOMContentLoaded', function() {
    // 로딩 시간 측정
    const loadTime = performance.now();
    console.log(`페이지 로딩 시간: ${loadTime.toFixed(2)}ms`);
    
    // 느린 로딩 경고 (3초 이상)
    if (loadTime > 3000) {
        console.warn('페이지 로딩이 느립니다. 성능 최적화가 필요할 수 있습니다.');
    }
});

// 이미지 지연 로딩
document.addEventListener('DOMContentLoaded', function() {
    const images = document.querySelectorAll('img[data-src]');
    
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    imageObserver.unobserve(img);
                }
            });
        });
        
        images.forEach(img => imageObserver.observe(img));
    } else {
        // 폴백: IntersectionObserver를 지원하지 않는 브라우저
        images.forEach(img => {
            img.src = img.dataset.src;
            img.removeAttribute('data-src');
        });
    }
});

// 폼 제출 최적화 (중복 제출 방지)
document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        let submitted = false;
        
        form.addEventListener('submit', function(e) {
            if (submitted) {
                e.preventDefault();
                return false;
            }
            
            submitted = true;
            
            // 제출 버튼 비활성화
            const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 처리중...';
            }
            
            // 5초 후 다시 활성화 (서버 응답이 없을 경우)
            setTimeout(() => {
                submitted = false;
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = submitBtn.dataset.originalText || '제출';
                }
            }, 5000);
        });
    });
});

// 테이블 가상 스크롤링 (큰 데이터셋용)
function initVirtualScrolling(tableId, rowHeight = 50) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    if (rows.length <= 50) return; // 50개 이하면 가상 스크롤링 비활성화
    
    const container = document.createElement('div');
    container.style.height = '400px';
    container.style.overflow = 'auto';
    
    const viewport = document.createElement('div');
    viewport.style.height = `${rows.length * rowHeight}px`;
    viewport.style.position = 'relative';
    
    container.appendChild(viewport);
    table.parentNode.insertBefore(container, table);
    table.style.position = 'absolute';
    table.style.top = '0';
    
    let startIndex = 0;
    const visibleRows = Math.ceil(400 / rowHeight) + 2; // 버퍼 추가
    
    function updateVisibleRows() {
        const scrollTop = container.scrollTop;
        startIndex = Math.floor(scrollTop / rowHeight);
        const endIndex = Math.min(startIndex + visibleRows, rows.length);
        
        // 기존 행 제거
        tbody.innerHTML = '';
        
        // 보이는 행만 렌더링
        for (let i = startIndex; i < endIndex; i++) {
            tbody.appendChild(rows[i].cloneNode(true));
        }
        
        table.style.transform = `translateY(${startIndex * rowHeight}px)`;
    }
    
    container.addEventListener('scroll', updateVisibleRows);
    updateVisibleRows();
}

// 캐시 최적화
function cacheData(key, data, ttl = 300000) { // 5분 TTL
    const item = {
        data: data,
        timestamp: Date.now(),
        ttl: ttl
    };
    localStorage.setItem(key, JSON.stringify(item));
}

function getCachedData(key) {
    const item = localStorage.getItem(key);
    if (!item) return null;
    
    const parsed = JSON.parse(item);
    if (Date.now() - parsed.timestamp > parsed.ttl) {
        localStorage.removeItem(key);
        return null;
    }
    
    return parsed.data;
}

// AJAX 요청 최적화
function optimizedFetch(url, options = {}) {
    // 캐시 확인
    const cacheKey = `fetch_${url}`;
    const cached = getCachedData(cacheKey);
    
    if (cached && options.method !== 'POST') {
        return Promise.resolve(cached);
    }
    
    // 요청 중복 제거
    if (!window.pendingRequests) {
        window.pendingRequests = new Map();
    }
    
    if (window.pendingRequests.has(url)) {
        return window.pendingRequests.get(url);
    }
    
    const request = fetch(url, {
        ...options,
        headers: {
            'Cache-Control': 'max-age=300',
            ...options.headers
        }
    })
    .then(response => response.json())
    .then(data => {
        // GET 요청만 캐시
        if (!options.method || options.method === 'GET') {
            cacheData(cacheKey, data);
        }
        window.pendingRequests.delete(url);
        return data;
    })
    .catch(error => {
        window.pendingRequests.delete(url);
        throw error;
    });
    
    window.pendingRequests.set(url, request);
    return request;
}