/**
 * 휴가관리시스템 공통 JavaScript 파일
 */

document.addEventListener('DOMContentLoaded', function() {
    // 사이드바 토글 (모바일)
    const sidebarToggle = document.querySelector('[data-toggle="sidebar"]');
    const sidebar = document.getElementById('sidebar');
    
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('show');
        });
    }
    
    // 알림 메시지 자동 닫기
    const alerts = document.querySelectorAll('.alert-dismissible');
    
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.classList.add('opacity-0');
            setTimeout(function() {
                alert.remove();
            }, 300);
        }, 5000);
    });
    
    // DatePicker 기본 설정 (한국어)
    if (typeof flatpickr !== 'undefined') {
        flatpickr.localize({
            weekdays: {
                shorthand: ['일', '월', '화', '수', '목', '금', '토'],
                longhand: ['일요일', '월요일', '화요일', '수요일', '목요일', '금요일', '토요일']
            },
            months: {
                shorthand: ['1월', '2월', '3월', '4월', '5월', '6월', '7월', '8월', '9월', '10월', '11월', '12월'],
                longhand: ['1월', '2월', '3월', '4월', '5월', '6월', '7월', '8월', '9월', '10월', '11월', '12월']
            },
            firstDayOfWeek: 0,
            rangeSeparator: ' ~ ',
            time_24hr: true
        });
    }
    
    // 테이블 행 hover 효과
    const tableRows = document.querySelectorAll('table tbody tr');
    
    tableRows.forEach(function(row) {
        row.addEventListener('mouseenter', function() {
            this.classList.add('bg-gray-50');
        });
        
        row.addEventListener('mouseleave', function() {
            this.classList.remove('bg-gray-50');
        });
    });
    
    // 모달 닫기 버튼
    const modalCloseBtns = document.querySelectorAll('[data-dismiss="modal"]');
    
    modalCloseBtns.forEach(function(btn) {
        btn.addEventListener('click', function() {
            const modal = this.closest('.modal');
            if (modal) {
                modal.classList.add('hidden');
            }
        });
    });
    
    // 모달 외부 클릭 시 닫기
    const modals = document.querySelectorAll('.modal');
    
    modals.forEach(function(modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                this.classList.add('hidden');
            }
        });
    });
    
    // 모달 열기 버튼
    const modalOpenBtns = document.querySelectorAll('[data-toggle="modal"]');
    
    modalOpenBtns.forEach(function(btn) {
        btn.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const modal = document.querySelector(targetId);
            
            if (modal) {
                modal.classList.remove('hidden');
            }
        });
    });
    
    // 탭 전환
    const tabLinks = document.querySelectorAll('[data-toggle="tab"]');
    
    tabLinks.forEach(function(link) {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            const targetTab = document.querySelector(targetId);
            
            // 모든 탭 비활성화
            document.querySelectorAll('.tab-pane').forEach(function(tab) {
                tab.classList.add('hidden');
            });
            
            // 모든 탭 링크 비활성화
            document.querySelectorAll('[data-toggle="tab"]').forEach(function(tabLink) {
                tabLink.classList.remove('active');
                tabLink.classList.remove('text-primary');
                tabLink.classList.remove('border-primary');
                tabLink.classList.add('text-gray-500');
                tabLink.classList.add('border-transparent');
            });
            
            // 현재 탭 활성화
            if (targetTab) {
                targetTab.classList.remove('hidden');
                this.classList.add('active');
                this.classList.add('text-primary');
                this.classList.add('border-primary');
                this.classList.remove('text-gray-500');
                this.classList.remove('border-transparent');
            }
        });
    });
    
    // 활성 탭 초기화
    const activeTabLink = document.querySelector('[data-toggle="tab"].active');
    if (activeTabLink) {
        activeTabLink.click();
    }
});

/**
 * 날짜를 YYYY-MM-DD 형식으로 변환
 * @param {Date} date - 변환할 날짜
 * @returns {string} 변환된 문자열
 */
function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    
    return `${year}-${month}-${day}`;
}

/**
 * YYYY-MM-DD 형식의 문자열을 Date 객체로 변환
 * @param {string} dateString - 변환할 날짜 문자열
 * @returns {Date} 변환된 Date 객체
 */
function parseDate(dateString) {
    const parts = dateString.split('-');
    return new Date(parts[0], parts[1] - 1, parts[2]);
}

/**
 * 두 날짜 사이의 일수 계산 (시작일, 종료일 포함)
 * @param {Date} startDate - 시작일
 * @param {Date} endDate - 종료일
 * @returns {number} 일수
 */
function getDaysBetween(startDate, endDate) {
    const oneDay = 24 * 60 * 60 * 1000; // 밀리초 단위로 하루
    const diffDays = Math.round(Math.abs((startDate - endDate) / oneDay)) + 1;
    
    return diffDays;
}

/**
 * 날짜가 주말인지 확인
 * @param {Date} date - 확인할 날짜
 * @returns {boolean} 주말 여부
 */
function isWeekend(date) {
    const day = date.getDay();
    return day === 0 || day === 6; // 0: 일요일, 6: 토요일
}

/**
 * 숫자를 통화 형식으로 포맷팅 (한국어)
 * @param {number} number - 포맷팅할 숫자
 * @returns {string} 포맷팅된 문자열
 */
function formatCurrency(number) {
    return new Intl.NumberFormat('ko-KR', {
        style: 'currency',
        currency: 'KRW'
    }).format(number);
}
