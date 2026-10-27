// 트릿지 솔루션 성과보고서 자동화 프론트엔드 로직
document.addEventListener('DOMContentLoaded', () => {
  let appState = {
    records: [],
    kpis: {},
    config: { sheet_url: '', webhook_url: '' }
  };

  // 1. 초기 데이터 및 설정 로드
  fetchRecords();

  // 2. 탭 네비게이션 이벤트
  setupTabs();

  // 3. 버튼 이벤트 리스너 등록
  setupEventListeners();

  // ==========================================
  // API 호출 함수들
  // ==========================================
  async function fetchRecords() {
    try {
      const res = await fetch('/api/records');
      if (!res.ok) throw new Error('데이터를 불러오지 못했습니다.');
      const data = await res.json();
      appState.records = data.records || [];
      appState.kpis = data.kpis || {};
      appState.config = data.config || { sheet_url: '', webhook_url: '' };

      updateConfigUI();
      renderAll();
    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  function updateConfigUI() {
    const sheetInput = document.getElementById('input-gsheet-url');
    const webhookInput = document.getElementById('input-webhook-url');
    const openSheetSide = document.getElementById('btn-open-gsheet-link');
    const openSheetInput = document.getElementById('btn-open-gsheet-input');

    if (sheetInput && appState.config.sheet_url) {
      sheetInput.value = appState.config.sheet_url;
    }
    if (webhookInput && appState.config.webhook_url) {
      webhookInput.value = appState.config.webhook_url;
    }

    if (appState.config.sheet_url) {
      if (openSheetSide) {
        openSheetSide.href = appState.config.sheet_url;
        openSheetSide.style.display = 'inline-flex';
      }
      if (openSheetInput) {
        openSheetInput.href = appState.config.sheet_url;
        openSheetInput.style.display = 'inline-flex';
      }
      document.getElementById('sheet-sync-status-text').textContent = '구글 시트 연동 완료';
    } else {
      if (openSheetSide) openSheetSide.style.display = 'none';
      if (openSheetInput) openSheetInput.style.display = 'none';
      document.getElementById('sheet-sync-status-text').textContent = '구글 시트 미연동';
    }
  }

  async function syncGoogleSheets() {
    const urlInput = document.getElementById('input-gsheet-url');
    const url = urlInput.value.trim();
    if (!url) {
      showToast('구글 스프레드시트 URL을 입력해 주세요.', 'error');
      return;
    }

    const mode = document.querySelector('input[name="sync-mode"]:checked')?.value || 'overwrite';
    const syncBtn = document.getElementById('btn-sync-gsheet');
    const originalText = syncBtn.innerHTML;

    syncBtn.disabled = true;
    syncBtn.innerHTML = '⏳ 구글 시트에서 가져오는 중...';

    try {
      const res = await fetch('/api/google-sheets/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, mode })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || '구글 시트 동기화에 실패했습니다.');
      }

      showToast(`성공! 구글 시트로부터 ${data.imported_count}건의 최신 실적을 동기화했습니다.`, 'success');
      fetchRecords();
      switchTab('tab-overview');
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      syncBtn.disabled = false;
      syncBtn.innerHTML = originalText;
    }
  }

  async function saveWebhookUrl() {
    const webhookInput = document.getElementById('input-webhook-url');
    const webhookUrl = webhookInput.value.trim();

    try {
      const res = await fetch('/api/google-sheets/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ webhook_url: webhookUrl })
      });
      if (!res.ok) throw new Error('저장에 실패했습니다.');
      showToast('구글 시트 자동 적재 Webhook URL이 저장되었습니다!', 'success');
      fetchRecords();
    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  async function copyAppsScriptCode() {
    try {
      const res = await fetch('/api/google-sheets/script-code');
      const data = await res.json();
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(data.code);
        showToast('Apps Script 코드가 클립보드에 복사되었습니다! 구글 시트 [확장 프로그램 > Apps Script]에 붙여넣으세요.', 'success');
      } else {
        alert(data.code);
      }
    } catch (err) {
      showToast('코드 복사 실패: ' + err.message, 'error');
    }
  }

  async function downloadDocxReport() {
    const btns = [
      document.getElementById('btn-generate-docx-header'),
      document.getElementById('btn-generate-docx-main'),
      document.getElementById('btn-generate-docx-banner')
    ];

    btns.forEach(b => { if (b) b.disabled = true; });
    showToast('AI 분석 및 워드 보고서 생성 중입니다. 잠시만 기다려 주세요...', 'info');

    try {
      const res = await fetch('/api/generate-docx', { method: 'POST' });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || '보고서 생성에 실패했습니다.');
      }

      const blob = await res.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      const today = new Date().toISOString().slice(0, 10).replace(/-/g, '');
      a.download = `트릿지_솔루션_활용_성과보고서_${today}.docx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(downloadUrl);

      showToast('성과보고서(.docx)가 성공적으로 다운로드되었습니다!', 'success');
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      btns.forEach(b => { if (b) b.disabled = false; });
    }
  }

  async function resetSampleData() {
    if (!confirm('기본 예시 데이터(5개 부서 실적)로 복원하시겠습니까?')) return;
    try {
      const res = await fetch('/api/records/reset', { method: 'POST' });
      if (!res.ok) throw new Error('초기화 실패');
      showToast('기본 예시 데이터로 복원되었습니다.', 'success');
      fetchRecords();
    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  async function deleteRecord(id) {
    if (!confirm('해당 실적 항목을 삭제하시겠습니까?')) return;
    try {
      const res = await fetch(`/api/records/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('삭제 실패');
      showToast('삭제되었습니다.', 'info');
      fetchRecords();
    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  // ==========================================
  // 렌더링 함수들
  // ==========================================
  function renderAll() {
    renderKPIs();
    renderOverviewTable();
    renderSolutionProgress();
    renderMainTable();
  }

  function renderKPIs() {
    const kpis = appState.kpis;
    document.getElementById('kpi-financial').textContent = (kpis.total_financial_impact || 0).toLocaleString();
    document.getElementById('kpi-time').textContent = (kpis.total_time_saved || 0).toLocaleString();
    document.getElementById('kpi-db').textContent = (kpis.total_db_count || 0).toLocaleString();
    document.getElementById('kpi-satisfaction').textContent = (kpis.avg_satisfaction || 0.0).toFixed(1);
    document.getElementById('kpi-dept-coverage').textContent = `${kpis.department_count || 0}개 부서 (${kpis.total_count || 0}건) 참여 중`;
    document.getElementById('sidebar-record-count').textContent = kpis.total_count || 0;
    document.getElementById('overview-dept-count').textContent = `${kpis.department_count || 0}개 부서 참여`;
  }

  function renderOverviewTable() {
    const tbody = document.getElementById('tbody-overview-summary');
    if (!appState.records.length) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:#94A3B8; padding:24px;">취합된 데이터가 없습니다. 구글 시트를 연동하거나 새 실적을 입력해 주세요.</td></tr>';
      return;
    }

    tbody.innerHTML = appState.records.map(r => {
      const statusClass = r.status === '완료' ? 'status-done' : (r.status === '진행중' ? 'status-doing' : 'status-todo');
      const stars = '★'.repeat(r.satisfaction || 4) + '☆'.repeat(5 - (r.satisfaction || 4));
      return `
        <tr>
          <td><strong>${escapeHtml(r.department)}</strong></td>
          <td><span class="badge blue">${escapeHtml(r.solution)}</span></td>
          <td><span class="table-tag ${statusClass}">${escapeHtml(r.status)}</span></td>
          <td>${r.valid_db_count || 0}개사</td>
          <td style="color:#10B981; font-weight:600;">+${(r.financial_impact || 0).toLocaleString()}만원</td>
          <td style="color:#3B82F6; font-weight:600;">${r.time_saved_hours || 0}시간</td>
          <td style="color:#F59E0B;">${stars}</td>
        </tr>
      `;
    }).join('');
  }

  function renderSolutionProgress() {
    const container = document.getElementById('solution-progress-list');
    const breakdown = appState.kpis.solution_breakdown || {};
    const total = appState.kpis.total_count || 1;

    const colors = {
      '트릿지 아이': 'linear-gradient(90deg, #3B82F6, #06B6D4)',
      '트릿지 아크': 'linear-gradient(90deg, #8B5CF6, #EC4899)',
      'Data Analytics': 'linear-gradient(90deg, #10B981, #3B82F6)',
      '수출바우처 연계': 'linear-gradient(90deg, #F59E0B, #EF4444)',
      '기타': 'linear-gradient(90deg, #94A3B8, #CBD5E1)'
    };

    const keys = Object.keys(breakdown);
    if (!keys.length) {
      container.innerHTML = '<p style="color:#94A3B8; font-size:0.85rem;">솔루션 데이터가 없습니다.</p>';
      return;
    }

    container.innerHTML = keys.map(k => {
      const count = breakdown[k];
      const pct = Math.round((count / total) * 100);
      const bg = colors[k] || colors['기타'];
      return `
        <div class="solution-progress-item">
          <div class="sol-label-row">
            <span>${escapeHtml(k)}</span>
            <span style="color:#94A3B8;">${count}건 (${pct}%)</span>
          </div>
          <div class="progress-track">
            <div class="progress-fill" style="width: ${pct}%; background: ${bg};"></div>
          </div>
        </div>
      `;
    }).join('');
  }

  function renderMainTable() {
    const tbody = document.getElementById('tbody-main-records');
    const filter = (document.getElementById('filter-search')?.value || '').toLowerCase().trim();

    let filtered = appState.records;
    if (filter) {
      filtered = filtered.filter(r => 
        (r.department && r.department.toLowerCase().includes(filter)) ||
        (r.author && r.author.toLowerCase().includes(filter)) ||
        (r.target && r.target.toLowerCase().includes(filter)) ||
        (r.goal && r.goal.toLowerCase().includes(filter))
      );
    }

    if (!filtered.length) {
      tbody.innerHTML = '<tr><td colspan="11" style="text-align:center; color:#94A3B8; padding:32px;">검색된 실적이 없습니다.</td></tr>';
      return;
    }

    tbody.innerHTML = filtered.map(r => {
      const statusClass = r.status === '완료' ? 'status-done' : (r.status === '진행중' ? 'status-doing' : 'status-todo');
      return `
        <tr>
          <td><strong>${escapeHtml(r.department)}</strong></td>
          <td>${escapeHtml(r.author || '-')}</td>
          <td><span class="badge blue">${escapeHtml(r.solution)}</span></td>
          <td style="max-width: 240px; font-size:0.85rem;" title="${escapeHtml(r.goal)}">
            <div style="font-weight:600;">${escapeHtml(r.target)}</div>
            <div style="color:#94A3B8; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(r.goal)}</div>
          </td>
          <td><span class="table-tag ${statusClass}">${escapeHtml(r.status)}</span></td>
          <td>${r.valid_db_count || 0}</td>
          <td>${r.action_count || 0}</td>
          <td style="color:#10B981; font-weight:600;">${(r.financial_impact || 0).toLocaleString()}</td>
          <td style="color:#3B82F6;">${r.time_saved_hours || 0}h</td>
          <td>⭐ ${r.satisfaction || 4}</td>
          <td>
            <button class="btn-ghost btn-delete" data-id="${r.id}" style="padding:4px 8px; color:#F43F5E; border-color:rgba(244,63,94,0.3);">
              삭제
            </button>
          </td>
        </tr>
      `;
    }).join('');

    document.querySelectorAll('.btn-delete').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const id = e.currentTarget.getAttribute('data-id');
        deleteRecord(id);
      });
    });
  }

  // ==========================================
  // 이벤트 리스너 및 탭 제어
  // ==========================================
  function setupTabs() {
    document.querySelectorAll('.nav-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const tabId = btn.getAttribute('data-tab');
        switchTab(tabId);
      });
    });

    document.getElementById('btn-go-to-input')?.addEventListener('click', () => {
      switchTab('tab-input');
    });
  }

  function switchTab(tabId) {
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

    const targetNav = document.querySelector(`.nav-btn[data-tab="${tabId}"]`);
    const targetPane = document.getElementById(tabId);

    if (targetNav) targetNav.classList.add('active');
    if (targetPane) targetPane.classList.add('active');
  }

  function setupEventListeners() {
    // 1. 구글 시트 동기화 버튼
    document.getElementById('btn-sync-gsheet')?.addEventListener('click', syncGoogleSheets);

    // 2. Webhook 저장 및 스크립트 복사
    document.getElementById('btn-save-webhook')?.addEventListener('click', saveWebhookUrl);
    document.getElementById('btn-show-script-modal')?.addEventListener('click', copyAppsScriptCode);

    // 3. 워드 보고서 생성 버튼들
    document.getElementById('btn-generate-docx-header')?.addEventListener('click', downloadDocxReport);
    document.getElementById('btn-generate-docx-main')?.addEventListener('click', downloadDocxReport);
    document.getElementById('btn-generate-docx-banner')?.addEventListener('click', downloadDocxReport);

    // 4. 샘플 데이터 복원
    document.getElementById('btn-reset-sample')?.addEventListener('click', resetSampleData);

    // 5. 구글 시트 템플릿 다운로드
    const downloadTemplateAction = () => {
      window.location.href = '/api/download-template';
      showToast('표준 구글 시트 취합 서식이 다운로드되었습니다.', 'success');
    };
    document.getElementById('btn-download-template-side')?.addEventListener('click', downloadTemplateAction);
    document.getElementById('btn-download-template-main')?.addEventListener('click', downloadTemplateAction);

    // 6. 검색 필터
    document.getElementById('filter-search')?.addEventListener('input', () => {
      renderMainTable();
    });

    // 7. 직접 입력 폼 제출
    const form = document.getElementById('record-form');
    form?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const newRecord = {
        department: document.getElementById('form-dept').value,
        author: document.getElementById('form-author').value,
        solution: document.getElementById('form-solution').value,
        period: document.getElementById('form-period').value || '2026년 하반기',
        target: document.getElementById('form-target').value,
        goal: document.getElementById('form-goal').value,
        status: document.getElementById('form-status').value,
        activity: document.getElementById('form-activity').value || '-',
        valid_db_count: parseInt(document.getElementById('form-db').value, 10) || 0,
        action_count: parseInt(document.getElementById('form-action').value, 10) || 0,
        financial_impact: parseFloat(document.getElementById('form-financial').value) || 0,
        time_saved_hours: parseFloat(document.getElementById('form-time').value) || 0,
        qualitative_insight: document.getElementById('form-insight').value,
        satisfaction: parseInt(document.getElementById('form-satisfaction').value, 10) || 4,
        next_plan: document.getElementById('form-next').value || '-',
        issue_and_request: document.getElementById('form-issue').value || '-'
      };

      try {
        const res = await fetch('/api/records', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(newRecord)
        });
        const resData = await res.json();
        if (!res.ok) throw new Error('등록에 실패했습니다.');

        const gsheetMsg = resData.google_sheet_synced ? ' (구글 스프레드시트에도 자동 적재 완료!)' : '';
        showToast('실적이 등록되었습니다!' + gsheetMsg, 'success');

        form.reset();
        fetchRecords();
        switchTab('tab-table');
      } catch (err) {
        showToast(err.message, 'error');
      }
    });
  }

  // ==========================================
  // 유틸리티
  // ==========================================
  function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icon = type === 'success' ? '✅' : (type === 'error' ? '⚠️' : 'ℹ️');
    toast.innerHTML = `<span>${icon}</span><span>${escapeHtml(message)}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
});
