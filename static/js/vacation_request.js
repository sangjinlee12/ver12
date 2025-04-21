/**
 * 휴가 신청 관련 JavaScript 기능
 */

document.addEventListener('DOMContentLoaded', function() {
    // 필요한 DOM 요소
    const vacationForm = document.getElementById('vacationForm');
    const startDateInput = document.getElementById('start_date');
    const endDateInput = document.getElementById('end_date');
    const typeSelect = document.getElementById('type');
    const daysHiddenInput = document.getElementById('days');
    const calculatedDaysElement = document.getElementById('calculatedDays');
    const calculateBtn = document.getElementById('calculateBtn');
    
    // 요소가 존재하지 않으면 종료
    if (!vacationForm) return;
    
    // 유형이 반차일 경우 종료일을 시작일과 동일하게 설정
    if (typeSelect) {
        typeSelect.addEventListener('change', function() {
            if (this.value === '반차(오전)' || this.value === '반차(오후)') {
                if (startDateInput && endDateInput) {
                    endDateInput.value = startDateInput.value;
                    endDateInput.disabled = true;
                    
                    // 반차는 0.5일로 고정
                    if (calculatedDaysElement && daysHiddenInput) {
                        calculatedDaysElement.textContent = '0.5일';
                        daysHiddenInput.value = '0.5';
                    }
                }
            } else {
                if (endDateInput) {
                    endDateInput.disabled = false;
                }
                calculateVacationDays();
            }
        });
    }
    
    // 날짜 변경 시 자동 계산
    if (startDateInput) {
        startDateInput.addEventListener('change', calculateVacationDays);
    }
    
    if (endDateInput) {
        endDateInput.addEventListener('change', calculateVacationDays);
    }
    
    // 계산 버튼 클릭 시 계산
    if (calculateBtn) {
        calculateBtn.addEventListener('click', calculateVacationDays);
    }
    
    // 휴가 일수 계산 함수
    function calculateVacationDays() {
        if (!startDateInput || !endDateInput || !typeSelect || !daysHiddenInput || !calculatedDaysElement) {
            return;
        }
        
        const startDate = startDateInput.value;
        const endDate = endDateInput.value;
        const type = typeSelect.value;
        
        if (!startDate || !endDate) return;
        
        // 반차인 경우 0.5일로 고정
        if (type === '반차(오전)' || type === '반차(오후)') {
            calculatedDaysElement.textContent = '0.5일';
            daysHiddenInput.value = '0.5';
            return;
        }
        
        // API를 통해 휴가 일수 계산
        fetch('/employee/calculate-vacation-days', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                start_date: startDate,
                end_date: endDate,
                type: type
            }),
        })
        .then(response => response.json())
        .then(data => {
            calculatedDaysElement.textContent = data.days + '일';
            daysHiddenInput.value = data.days;
            
            // 0일인 경우 (주말/공휴일만 있는 경우) 경고 표시
            if (data.days === 0) {
                calculatedDaysElement.innerHTML = '<span class="text-red-600">0일 (선택한 기간에 평일이 없습니다)</span>';
            }
        })
        .catch(error => {
            console.error('Error:', error);
            calculatedDaysElement.textContent = '계산 오류';
        });
    }
    
    // 폼 제출 전 유효성 검사
    if (vacationForm) {
        vacationForm.addEventListener('submit', function(e) {
            if (!daysHiddenInput || !daysHiddenInput.value || daysHiddenInput.value === '0') {
                e.preventDefault();
                alert('휴가 일수가 0일입니다. 날짜를 확인해주세요.');
            }
        });
    }
    
    // 초기 계산
    if (startDateInput && endDateInput && startDateInput.value && endDateInput.value) {
        calculateVacationDays();
    }
    
    // 특별휴가 설명 표시
    if (typeSelect) {
        const specialVacationInfo = document.getElementById('specialVacationInfo');
        
        if (specialVacationInfo) {
            typeSelect.addEventListener('change', function() {
                if (this.value === '특별휴가') {
                    specialVacationInfo.classList.remove('hidden');
                } else {
                    specialVacationInfo.classList.add('hidden');
                }
            });
        }
    }
});

/**
 * 휴가 승인/반려 관련 함수
 */

// 휴가 승인 상태 변경 시 확인
function confirmStatusChange(form) {
    const statusSelect = form.querySelector('#status');
    if (!statusSelect) return true;
    
    const status = statusSelect.value;
    
    if (status === '승인됨') {
        return confirm('휴가를 승인하시겠습니까?');
    } else if (status === '반려됨') {
        return confirm('휴가를 반려하시겠습니까?');
    }
    
    return true;
}

// 휴가 취소 확인
function confirmCancelVacation() {
    return confirm('휴가 신청을 취소하시겠습니까? 이 작업은 되돌릴 수 없습니다.');
}
