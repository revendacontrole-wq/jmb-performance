const app = {
  token: localStorage.getItem('jmb_token') || null,
  currentUser: JSON.parse(localStorage.getItem('jmb_user') || 'null'),
  currentPreviewToken: null,
  chartInstance: null,
  selectedFile: null,

  init() {
    if (this.token && this.currentUser) {
      this.showAppHeader();
      this.routeUserView();
    } else {
      this.showView('viewLogin');
    }
  },

  showView(viewId) {
    ['viewLogin', 'viewCollaborator', 'viewSupervisor', 'viewAdmin'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.style.display = (id === viewId) ? 'block' : 'none';
    });
  },

  showAppHeader() {
    const header = document.getElementById('appHeader');
    if (header && this.currentUser) {
      header.style.display = 'flex';
      document.getElementById('headerUserName').textContent = this.currentUser.name;
      document.getElementById('headerUserCpf').textContent = this.currentUser.masked_cpf;
      document.getElementById('roleBadge').textContent = this.currentUser.role;
    }
  },

  routeUserView() {
    if (!this.currentUser) return;
    const role = this.currentUser.role;

    if (role === 'ADMIN') {
      this.showView('viewAdmin');
      this.loadAdminDashboard();
    } else if (role === 'SUPERVISOR') {
      this.showView('viewSupervisor');
      this.loadSupervisorDashboard();
    } else {
      this.showView('viewCollaborator');
      this.loadCollaboratorDashboard();
    }
  },

  togglePassword() {
    const input = document.getElementById('inputPassword');
    input.type = input.type === 'password' ? 'text' : 'password';
  },

  quickLogin(cpf, password) {
    document.getElementById('inputCpf').value = cpf;
    document.getElementById('inputPassword').value = password;
    this.handleLogin(new Event('submit'));
  },

  async handleLogin(e) {
    if (e) e.preventDefault();
    const cpf = document.getElementById('inputCpf').value;
    const password = document.getElementById('inputPassword').value;
    const errEl = document.getElementById('loginError');

    errEl.style.display = 'none';

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cpf, password })
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'Falha na autenticação.');
      }

      this.token = data.access_token;
      this.currentUser = data.user;
      localStorage.setItem('jmb_token', this.token);
      localStorage.setItem('jmb_user', JSON.stringify(this.currentUser));

      this.showAppHeader();
      this.routeUserView();
    } catch (err) {
      errEl.textContent = err.message;
      errEl.style.display = 'block';
    }
  },

  logout() {
    localStorage.removeItem('jmb_token');
    localStorage.removeItem('jmb_user');
    this.token = null;
    this.currentUser = null;
    document.getElementById('appHeader').style.display = 'none';
    this.showView('viewLogin');
  },

  getAuthHeaders() {
    return {
      'Authorization': `Bearer ${this.token}`,
      'Content-Type': 'application/json'
    };
  },

  // --- COLLABORATOR DASHBOARD TABS ---
  switchCollabTab(tabName) {
    const tabs = ['desempenho', 'feedback', 'treinamentos', 'campanhas'];
    tabs.forEach(t => {
      const btn = document.getElementById(`btnTabCollab${t.charAt(0).toUpperCase() + t.slice(1)}`);
      const sec = document.getElementById(`tabCollab${t.charAt(0).toUpperCase() + t.slice(1)}`);
      if (btn) btn.classList.toggle('active', t === tabName);
      if (sec) sec.style.display = (t === tabName) ? 'block' : 'none';
    });

    if (tabName === 'desempenho' && !this.chartInstance) {
      this.loadHistoryChart();
    }
  },

  // --- COLLABORATOR DASHBOARD DATA ---
  async loadCollaboratorDashboard(competencia = null) {
    try {
      let url = '/api/collaborator/dashboard';
      if (competencia) url += `?competencia=${encodeURIComponent(competencia)}`;

      const res = await fetch(url, { headers: this.getAuthHeaders() });
      if (!res.ok) return;

      const data = await res.json();

      document.getElementById('collabGreeting').textContent = `Olá, ${data.name}`;
      document.getElementById('collabSubtext').textContent = `Competência ${data.competencia}`;

      document.getElementById('valPerfGeral').textContent = `${data.performance_pct.toFixed(1)}%`;
      const elRating = document.getElementById('valRatingTag');
      if (elRating) elRating.textContent = data.rating || 'Rating B';
      document.getElementById('valRvPrevista').textContent = `R$ ${data.rv_prevista.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;
      document.getElementById('valRanking').textContent = `${data.ranking_pos}º`;
      document.getElementById('subRanking').textContent = `de ${data.ranking_total} colaboradores`;

      // Update Competence Select Options
      const sel = document.getElementById('selectCompetenciaCollab');
      if (data.available_competencias && data.available_competencias.length > 0) {
        sel.innerHTML = data.available_competencias.map(c => `<option value="${c}" ${c === data.competencia ? 'selected' : ''}>${c}</option>`).join('');
      }

      // Default feedback date picker to today YYYY-MM-DD
      const dateInput = document.getElementById('inputFeedbackDate');
      if (dateInput && !dateInput.value) {
        const today = new Date().toISOString().split('T')[0];
        dateInput.value = today;
      }

      // Render 6 Indicators Grid
      const container = document.getElementById('containerIndicators');
      container.innerHTML = data.indicators.map(ind => `
        <div class="indicator-card">
          <div class="ind-head">
            <span class="ind-name">${ind.label}</span>
            <span class="badge-status status-${ind.status.toLowerCase()}">${ind.status}</span>
          </div>
          <div class="ind-metrics">
            <div class="ind-metric-box">
              <label>Resultado Atual</label>
              <span>${ind.current_val}</span>
            </div>
            <div class="ind-metric-box" style="text-align: right;">
              <label>Meta</label>
              <span style="color: var(--text-muted);">${ind.meta_val}</span>
            </div>
          </div>
          <div class="progress-bar-bg">
            <div class="progress-bar-fill" style="width: ${Math.min(100, ind.pct)}%; background-color: ${ind.status === 'VERDE' ? '#10B981' : (ind.status === 'AMARELO' ? '#F59E0B' : '#EF4444')};"></div>
          </div>
          <div class="ind-note">${ind.impact_note || ''}</div>
        </div>
      `).join('');

      // Store breakdown data for modal
      this.currentBreakdown = data.breakdown;

      // Load Daily Indicators Breakdown
      this.loadCollaboratorDaily(data.competencia);

      // Load Extra Indicators (Reposição, Mapas, Entregas)
      this.loadCollaboratorExtraIndicators(data.competencia);

      // Load Collaborator's Own Feedbacks History
      this.loadMyFeedbacks(data.competencia);

      // Load Collaborator Trainings/PDFs
      this.loadCollaboratorTrainings();

      // Load History Chart
      this.loadHistoryChart();

      // Load Campaigns
      this.loadCampaigns();

      // Set default tab to 'desempenho'
      this.switchCollabTab('desempenho');

    } catch (err) {
      console.error('Error loading collaborator dashboard:', err);
    }
  },

  async loadCollaboratorExtraIndicators(competencia) {
    try {
      let url = '/api/collaborator/extra-indicators';
      if (competencia) url += `?competencia=${encodeURIComponent(competencia)}`;

      const res = await fetch(url, { headers: this.getAuthHeaders() });
      if (!res.ok) return;

      const data = await res.json();
      
      const mapasEl = document.getElementById('extraMapas');
      const entregasEl = document.getElementById('extraEntregas');
      const caixasEl = document.getElementById('extraCaixas');
      const repQtdEl = document.getElementById('extraReposicaoQtd');
      const repPctEl = document.getElementById('extraReposicaoPct');
      const badgeStatusEl = document.getElementById('badgeExtraStatus');

      if (mapasEl) mapasEl.textContent = data.mapas || '0';
      if (entregasEl) entregasEl.textContent = data.entregas || '0';
      if (caixasEl) caixasEl.textContent = data.caixas ? data.caixas.toLocaleString('pt-BR') : '0';
      if (repQtdEl) repQtdEl.textContent = data.reposicao_qtd || '0';
      if (repPctEl) repPctEl.textContent = `${data.reposicao_pct ? data.reposicao_pct.toFixed(1) : '0.0'}%`;

      if (badgeStatusEl) {
        badgeStatusEl.className = `badge-status status-${(data.reposicao_status || 'VERDE').toLowerCase()}`;
        badgeStatusEl.textContent = data.has_data ? 'DADOS CONSOLIDADOS' : 'SEM REPOSIÇÃO REGISTRADA';
      }

    } catch (err) {
      console.error('Error loading extra indicators:', err);
    }
  },

  async loadCollaboratorDaily(competencia) {
    try {
      let url = '/api/collaborator/daily';
      if (competencia) url += `?competencia=${encodeURIComponent(competencia)}`;

      const res = await fetch(url, { headers: this.getAuthHeaders() });
      if (!res.ok) return;

      const dailyList = await res.json();
      const tbody = document.getElementById('tbodyDailyBreakdown');

      if (!dailyList || dailyList.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; color:var(--text-muted);">Nenhum registro diário para esta competência.</td></tr>';
        document.getElementById('badgeDiasTrabalhados').textContent = '0 DIAS COM ROTA';
        return;
      }

      const workedDays = dailyList.filter(d => d.rv_dia > 0 || (d.mapa && d.mapa !== '-')).length;
      document.getElementById('badgeDiasTrabalhados').textContent = `${workedDays} DIAS COM ROTA`;

      tbody.innerHTML = dailyList.map(d => {
        const isWorked = d.rv_dia > 0 || (d.mapa && d.mapa !== '-');
        const badgeClass = isWorked ? 'status-verde' : 'status-amarelo';
        const badgeText = isWorked ? 'TRABALHADO' : 'SEM ROTA';
        const rvDiaText = d.rv_dia > 0 ? `R$ ${d.rv_dia.toFixed(2)}` : '-';
        const rvAcumText = d.rv_acumulada > 0 ? `R$ ${d.rv_acumulada.toFixed(2)}` : '-';

        // Daily indicators tags (Ajudantes, Hora Fim, Janela JL, Taxa Caixa, Devolução, Raio)
        const ajuText = d.qtd_ajudantes ? `${d.qtd_ajudantes} Aju` : '1 Aju';
        const jlBadgeClass = d.bateu_jl === 'Sim' ? 'status-verde' : 'status-amarelo';
        const jlText = d.bateu_jl === 'Sim' ? 'JL OK' : 'JL NOK';
        const horaText = d.hora_encerramento && d.hora_encerramento !== '--:--' ? `⏱️ ${d.hora_encerramento}` : '';
        const taxaText = d.taxa_caixa ? `R$ ${d.taxa_caixa.toFixed(2)}/cx` : 'R$ 0,14/cx';

        const devClass = d.devolucao_status === 'VERDE' ? 'status-verde' : 'status-vermelho';
        const devText = d.devolucao_status === 'VERDE' ? 'Devol. OK' : 'Devol. Alta';

        const raioClass = d.raio_status === 'VERDE' ? 'status-verde' : (d.raio_status === 'AMARELO' ? 'status-amarelo' : 'status-vermelho');
        const raioText = d.raio_status === 'VERDE' ? 'Raio OK' : 'Raio Alerta';

        const isMotorista = this.currentUser && this.currentUser.role === 'MOTORISTA';

        const indicatorsCell = isWorked ? `
          <div style="display: flex; gap: 0.35rem; align-items: center; flex-wrap: wrap; font-size: 0.75rem;">
            <span style="background: #E2E8F0; padding: 0.15rem 0.4rem; border-radius: 4px; font-weight: 600;">👥 ${ajuText}</span>
            <span style="background: #FEF3C7; color: #92400E; padding: 0.15rem 0.4rem; border-radius: 4px; font-weight: 700;">🏷️ ${taxaText}</span>
            ${horaText ? `<span style="background: #F1F5F9; padding: 0.15rem 0.4rem; border-radius: 4px;">${horaText}</span>` : ''}
            <span class="badge-status ${jlBadgeClass}" style="font-size: 0.7rem; padding: 0.15rem 0.4rem;">${jlText}</span>
            <span class="badge-status ${devClass}" style="font-size: 0.7rem; padding: 0.15rem 0.4rem;">${devText}</span>
            ${isMotorista ? `<span class="badge-status ${raioClass}" style="font-size: 0.7rem; padding: 0.15rem 0.4rem;">${raioText}</span>` : ''}
          </div>
        ` : '<span style="color: var(--text-muted); font-size: 0.8rem;">-</span>';

        return `
          <tr>
            <td><strong>Dia ${String(d.day_num).padStart(2, '0')}</strong></td>
            <td>${d.date_str}</td>
            <td><code>${d.mapa || '-'}</code></td>
            <td><strong>${d.caixas > 0 ? d.caixas.toFixed(0) + ' cx' : '-'}</strong></td>
            <td>${indicatorsCell}</td>
            <td style="color: ${d.rv_dia > 0 ? 'var(--primary)' : 'inherit'}; font-weight: ${d.rv_dia > 0 ? '700' : 'normal'};">${rvDiaText}</td>
            <td style="font-weight: 700; color: #0F172A;">${rvAcumText}</td>
            <td><span class="badge-status ${badgeClass}">${badgeText}</span></td>
          </tr>
        `;
      }).join('');

    } catch (err) {
      console.error('Error loading daily breakdown:', err);
    }
  },

  // --- TRAININGS / PDFS MODULE ---
  async loadCollaboratorTrainings(category = null) {
    try {
      let url = '/api/trainings';
      if (category && category !== 'Todas') url += `?category=${encodeURIComponent(category)}`;

      const res = await fetch(url, { headers: this.getAuthHeaders() });
      if (!res.ok) return;

      const list = await res.json();
      const container = document.getElementById('containerTrainingsCollab');

      if (!list || list.length === 0) {
        container.innerHTML = '<div style="color: var(--text-muted); grid-column: 1/-1; padding: 1rem;">Nenhum manual ou treinamento disponível nesta categoria.</div>';
        return;
      }

      container.innerHTML = list.map(tr => {
        const isPdf = tr.file_filename.toLowerCase().endsWith('.pdf');
        const icon = isPdf ? '📄' : (tr.file_filename.toLowerCase().endsWith('.mp4') ? '🎥' : '📁');

        return `
          <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.25rem; display: flex; flex-direction: column; justify-content: space-between; position: relative;">
            <div>
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
                <span style="font-size: 1.8rem;">${icon}</span>
                <span style="font-size: 0.75rem; font-weight: 700; background: #DBEAFE; color: #1E40AF; padding: 0.2rem 0.5rem; border-radius: 6px;">${tr.category}</span>
              </div>
              <h4 style="margin: 0.25rem 0 0.5rem 0; font-size: 1rem; color: #0F172A; line-height: 1.3;">${tr.title}</h4>
              <p style="font-size: 0.85rem; color: var(--text-muted); margin: 0 0 1rem 0; line-height: 1.4;">
                ${tr.description || 'Sem descrição cadastrada.'}
              </p>
            </div>
            <div>
              <div style="font-size: 0.75rem; color: #64748B; margin-bottom: 0.75rem; display: flex; justify-content: space-between;">
                <span>📅 ${tr.created_at}</span>
                <span>📦 ${tr.file_size_formatted}</span>
              </div>
              <a href="${tr.file_url}" target="_blank" class="btn-primary" style="display: inline-block; text-align: center; text-decoration: none; width: 100%; box-sizing: border-box; font-size: 0.85rem; padding: 0.6rem 1rem;">
                ⬇️ VISUALIZAR / BAIXAR MATERIAL
              </a>
            </div>
          </div>
        `;
      }).join('');

    } catch (err) {
      console.error('Error loading trainings for collab:', err);
    }
  },

  async handleTrainingUpload(e) {
    if (e) e.preventDefault();
    const title = document.getElementById('inputTrainingTitle').value;
    const category = document.getElementById('selectTrainingCategory').value;
    const desc = document.getElementById('textareaTrainingDesc').value;
    const urlInput = document.getElementById('inputTrainingUrl');
    let urlVal = urlInput ? urlInput.value.trim() : '';
    const fileInput = document.getElementById('fileTraining');
    const msgEl = document.getElementById('trainingUploadMsg');
    const btn = document.getElementById('btnSubmitTraining');

    if (!title || title.trim().length < 3) {
      alert('Por favor, informe um Título com no mínimo 3 caracteres.');
      return;
    }

    if (urlVal && !urlVal.startsWith('http://') && !urlVal.startsWith('https://')) {
      urlVal = 'https://' + urlVal;
    }

    btn.disabled = true;
    btn.textContent = 'PUBLICANDO MATERIAL...';
    msgEl.style.display = 'none';

    try {
      let reqBody;
      let headers = {
        'Authorization': `Bearer ${this.token}`
      };

      if (fileInput.files[0]) {
        const file = fileInput.files[0];
        if (file.size > 3.5 * 1024 * 1024) {
          alert(`⚠️ O arquivo "${file.name}" possui ${(file.size / (1024 * 1024)).toFixed(1)} MB. O limite para upload direto no servidor é 3.0 MB.\n\nPor favor, insira o Link do documento (Google Drive / OneDrive) no campo acima.`);
          btn.disabled = false;
          btn.textContent = 'PUBLICAR MATERIAL';
          return;
        }

        const formData = new FormData();
        formData.append('title', title.trim());
        formData.append('category', category);
        formData.append('description', desc ? desc.trim() : '');
        if (urlVal) formData.append('file_url_input', urlVal);
        formData.append('file', file);
        reqBody = formData;
      } else {
        headers['Content-Type'] = 'application/json';
        reqBody = JSON.stringify({
          title: title.trim(),
          category: category,
          description: desc ? desc.trim() : '',
          file_url: urlVal || '',
          filename: urlVal ? 'Link do Documento / Vídeo' : 'Instrução em Texto'
        });
      }

      const res = await fetch('/api/trainings', {
        method: 'POST',
        headers: headers,
        body: reqBody
      });

      let data = {};
      const contentType = res.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        data = await res.json();
      } else {
        const text = await res.text();
        if (!res.ok) throw new Error(`Erro no servidor (${res.status}): ${text.substring(0, 120)}`);
      }
      if (!res.ok) throw new Error(data.detail || 'Erro ao publicar treinamento.');

      msgEl.style.background = '#ECFDF5';
      msgEl.style.color = '#065F46';
      msgEl.style.border = '1px solid #A7F3D0';
      msgEl.textContent = '✅ Material publicado com sucesso! Já está disponível para a equipe.';
      msgEl.style.display = 'block';

      // Clear form inputs
      document.getElementById('inputTrainingTitle').value = '';
      document.getElementById('textareaTrainingDesc').value = '';
      if (urlInput) urlInput.value = '';
      document.getElementById('fileTraining').value = '';

      // Reload lists for both Admin and Collaborator views
      this.loadAdminTrainings();
      this.loadCollaboratorTrainings();

    } catch (err) {
      msgEl.style.background = '#FEF2F2';
      msgEl.style.color = '#991B1B';
      msgEl.style.border = '1px solid #FCA5A5';
      msgEl.textContent = `Erro: ${err.message}`;
      msgEl.style.display = 'block';
    } finally {
      btn.disabled = false;
      btn.textContent = 'PUBLICAR MATERIAL';
    }
  },

  async loadAdminTrainings() {
    try {
      const res = await fetch('/api/trainings', { headers: this.getAuthHeaders() });
      if (!res.ok) return;

      const list = await res.json();
      const tbody = document.getElementById('tbodyAdminTrainings');

      if (!list || list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:var(--text-muted);">Nenhum material de treinamento publicado ainda.</td></tr>';
        return;
      }

      tbody.innerHTML = list.map(tr => `
        <tr>
          <td><strong>${tr.title}</strong><br><small style="color:var(--text-muted);">${tr.description || ''}</small></td>
          <td><span style="font-size:0.75rem; font-weight:600; background:#DBEAFE; color:#1E40AF; padding:0.2rem 0.5rem; border-radius:4px;">${tr.category}</span></td>
          <td><code>${tr.file_filename}</code></td>
          <td>${tr.file_size_formatted}</td>
          <td><small>${tr.created_at}</small></td>
          <td>${tr.uploaded_by_name}</td>
          <td>
            <div style="display:flex; gap:0.5rem;">
              <a href="${tr.file_url}" target="_blank" class="btn-primary" style="padding:0.3rem 0.6rem; font-size:0.75rem; text-decoration:none;">VISUALIZAR</a>
              <button class="btn-logout" style="padding:0.3rem 0.6rem; font-size:0.75rem;" onclick="app.deleteTraining(${tr.id})">EXCLUIR</button>
            </div>
          </td>
        </tr>
      `).join('');

    } catch (err) {
      console.error('Error loading admin trainings:', err);
    }
  },

  async deleteTraining(trainingId) {
    if (!confirm('Deseja realmente remover este material de treinamento?')) return;

    try {
      const res = await fetch(`/api/trainings/${trainingId}`, {
        method: 'DELETE',
        headers: this.getAuthHeaders()
      });

      let data = {};
      const contentType = res.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        data = await res.json();
      } else {
        const text = await res.text();
        if (!res.ok) throw new Error(`Erro no servidor (${res.status}): ${text.substring(0, 120)}`);
      }

      if (!res.ok) throw new Error(data.detail || 'Erro ao remover treinamento.');

      alert('✅ Material removido com sucesso!');
      this.loadAdminTrainings();
      this.loadCollaboratorTrainings();

    } catch (err) {
      alert(`Erro: ${err.message}`);
    }
  },

  // --- FEEDBACK SUBMISSION & MY HISTORY ---
  async handleFeedbackSubmit(e) {
    if (e) e.preventDefault();
    const dateVal = document.getElementById('inputFeedbackDate').value;
    const category = document.getElementById('selectFeedbackCategory').value;
    const comment = document.getElementById('textareaFeedbackComment').value;
    const competencia = document.getElementById('selectCompetenciaCollab').value || 'Julho/2026';
    const msgEl = document.getElementById('feedbackMsg');
    const btn = document.getElementById('btnSubmitFeedback');

    if (!dateVal || !comment.trim()) return;

    // Convert YYYY-MM-DD to DD/MM/YYYY
    const parts = dateVal.split('-');
    const formattedIncidentDate = parts.length === 3 ? `${parts[2]}/${parts[1]}/${parts[0]}` : dateVal;

    btn.disabled = true;
    btn.textContent = 'ENVIANDO...';
    msgEl.style.display = 'none';

    try {
      const res = await fetch('/api/feedback', {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({
          competencia: competencia,
          incident_date: formattedIncidentDate,
          category: category,
          comment: comment.trim()
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Erro ao enviar feedback.');

      msgEl.style.background = '#ECFDF5';
      msgEl.style.color = '#065F46';
      msgEl.style.border = '1px solid #A7F3D0';
      msgEl.textContent = '✅ Feedback registrado com sucesso! A gestão irá analisar o seu relato.';
      msgEl.style.display = 'block';

      // Clear textarea
      document.getElementById('textareaFeedbackComment').value = '';

      // Reload feedbacks list
      this.loadMyFeedbacks(competencia);

    } catch (err) {
      msgEl.style.background = '#FEF2F2';
      msgEl.style.color = '#991B1B';
      msgEl.style.border = '1px solid #FCA5A5';
      msgEl.textContent = `Erro: ${err.message}`;
      msgEl.style.display = 'block';
    } finally {
      btn.disabled = false;
      btn.textContent = 'ENVIAR FEEDBACK';
    }
  },

  async loadMyFeedbacks(competencia = null) {
    try {
      let url = '/api/feedback/my';
      if (competencia) url += `?competencia=${encodeURIComponent(competencia)}`;

      const res = await fetch(url, { headers: this.getAuthHeaders() });
      if (!res.ok) return;

      const list = await res.json();
      const tbody = document.getElementById('tbodyMyFeedbacks');

      if (!list || list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:var(--text-muted);">Nenhum feedback registrado nesta competência.</td></tr>';
        return;
      }

      tbody.innerHTML = list.map(fb => {
        const statusClass = fb.status === 'RESOLVIDO' ? 'status-verde' : (fb.status === 'EM ANÁLISE' ? 'status-amarelo' : 'status-vermelho');
        const adminResp = fb.admin_notes ? `<span style="color:#047857; font-weight:600;">💬 ${fb.admin_notes}</span>` : '<span style="color:var(--text-muted); font-size:0.8rem;">Aguardando análise da gestão...</span>';

        return `
          <tr>
            <td><small>${fb.created_at}</small></td>
            <td><strong>${fb.incident_date}</strong></td>
            <td><span style="font-size:0.8rem; font-weight:600; background:#F1F5F9; padding:0.2rem 0.5rem; border-radius:4px;">${fb.category}</span></td>
            <td style="max-width:300px; font-size:0.85rem;">"${fb.comment}"</td>
            <td><span class="badge-status ${statusClass}">${fb.status}</span></td>
            <td>${adminResp}</td>
          </tr>
        `;
      }).join('');

    } catch (err) {
      console.error('Error loading my feedbacks:', err);
    }
  },

  openEntenderModal() {
    const b = this.currentBreakdown;
    if (!b) return;

    const content = document.getElementById('modalEntenderContent');
    content.innerHTML = `
      <div style="background: #F8FAFC; padding: 1rem; border-radius: 10px; margin-bottom: 1rem; border: 1px solid #E2E8F0;">
        <div style="display: flex; justify-content: space-between;">
          <span>RV Prevista Atual:</span>
          <strong style="color: var(--primary); font-size: 1.1rem;">R$ ${b.rv_prevista.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</strong>
        </div>
      </div>

      <!-- HIGHLIGHTED PAYMENT SCHEDULE BOX -->
      <div style="background: #F0F7FF; border: 1px solid #BFDBFE; border-left: 4px solid #0047BA; padding: 0.85rem 1rem; border-radius: 10px; margin-bottom: 1.25rem;">
        <div style="font-weight: 800; color: #0047BA; font-size: 0.88rem; margin-bottom: 0.25rem; display: flex; align-items: center; gap: 0.4rem;">
          <span>💳 HORÁRIO E DATA DE PAGAMENTO DA RV</span>
        </div>
        <p style="font-size: 0.82rem; color: #334155; margin: 0; line-height: 1.4;">
          O valor apurado da Remuneração Variável será creditado em conta / folha de pagamento até as <strong>17h00</strong> do <strong>5º dia útil</strong> do mês subsequente à apuração.
        </p>
      </div>

      <h4>✅ Indicadores Dentro da Meta</h4>
      <ul class="list-check">
        ${b.dentro_meta.map(item => `<li><span class="icon-ok">✓</span> ${item}</li>`).join('')}
      </ul>

      ${b.fora_meta.length > 0 ? `
        <h4 style="color: #B91C1C;">⚠️ Indicadores com Desvio</h4>
        <ul class="list-check">
          ${b.fora_meta.map(item => `<li><span class="icon-warn">✕</span> ${item}</li>`).join('')}
        </ul>
      ` : ''}

      <h4>📉 Fatores que Impactaram sua Remuneração</h4>
      <ul class="list-check">
        ${b.fatores_reducao.map(item => `<li><span class="icon-alert">!</span> ${item}</li>`).join('')}
      </ul>
    `;

    document.getElementById('modalEntender').classList.add('active');
  },

  closeEntenderModal() {
    document.getElementById('modalEntender').classList.remove('active');
  },

  async loadHistoryChart() {
    try {
      const res = await fetch('/api/collaborator/history', { headers: this.getAuthHeaders() });
      if (!res.ok) return;
      const history = await res.json();

      const labels = history.map(h => h.competencia);
      const dataPerf = history.map(h => h.performance_pct);
      const dataRv = history.map(h => h.rv_prevista);

      const ctx = document.getElementById('chartHistory').getContext('2d');
      if (this.chartInstance) this.chartInstance.destroy();

      this.chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [
            {
              label: 'Performance Geral (%)',
              data: dataPerf,
              borderColor: '#10B981',
              backgroundColor: 'rgba(16, 185, 129, 0.1)',
              fill: true,
              tension: 0.3,
              yAxisID: 'y'
            },
            {
              label: 'RV Prevista (R$)',
              data: dataRv,
              borderColor: '#0F172A',
              borderDash: [5, 5],
              fill: false,
              tension: 0.3,
              yAxisID: 'y1'
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: false,
              min: 50,
              max: 100,
              title: { display: true, text: 'Performance (%)' }
            },
            y1: {
              position: 'right',
              beginAtZero: true,
              title: { display: true, text: 'RV (R$)' },
              grid: { drawOnChartArea: false }
            }
          }
        }
      });
    } catch (err) {
      console.error('Error loading history chart:', err);
    }
  },

  async loadCampaigns() {
    try {
      const res = await fetch('/api/campaigns', { headers: this.getAuthHeaders() });
      if (!res.ok) return;
      const campaigns = await res.json();

      const container = document.getElementById('containerCampaigns');
      if (!campaigns || campaigns.length === 0) {
        container.innerHTML = '<div style="color: var(--text-muted); padding: 1rem;">Nenhuma campanha ativa no momento.</div>';
        return;
      }

      container.innerHTML = campaigns.map(c => `
        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 1rem; margin-bottom: 1rem;">
          <div style="display: flex; justify-content: space-between; font-weight: 700; margin-bottom: 0.4rem;">
            <span>${c.title}</span>
            <span class="badge-status ${c.status === 'Concluído' ? 'status-verde' : 'status-amarelo'}">${c.status}</span>
          </div>
          <div style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.5rem;">
            📅 Período: ${c.period} | 🎯 Meta: ${c.goal} | 🏆 Prêmio: <strong>${c.prize}</strong>
          </div>
          <div class="progress-bar-bg">
            <div class="progress-bar-fill" style="width: ${c.progress_pct}%; background-color: var(--primary);"></div>
          </div>
          <div style="font-size: 0.75rem; text-align: right; color: var(--text-muted); font-weight: 600;">Progresso: ${c.progress_pct}%</div>
        </div>
      `).join('');
    } catch (err) {
      console.error('Error loading campaigns:', err);
    }
  },

  // --- SUPERVISOR DASHBOARD ---
  async loadSupervisorDashboard() {
    try {
      const res = await fetch('/api/supervisor/dashboard', { headers: this.getAuthHeaders() });
      if (!res.ok) return;
      const data = await res.json();

      document.getElementById('supTotal').textContent = data.total_members;
      document.getElementById('supDentro').textContent = data.dentro_meta;
      document.getElementById('supAtencao').textContent = data.em_atencao;
      document.getElementById('supFora').textContent = data.fora_meta;

      const tbody = document.getElementById('tbodySupervisorTeam');
      tbody.innerHTML = data.team.map(m => `
        <tr>
          <td><strong>${m.ranking_pos}º</strong></td>
          <td><strong>${m.name}</strong></td>
          <td>${m.role}</td>
          <td><code>${m.masked_cpf}</code></td>
          <td>${m.performance_pct.toFixed(1)}%</td>
          <td><span style="font-weight:700; color:#0047BA; background:#EFF6FF; padding:0.15rem 0.4rem; border-radius:4px; border:1px solid #BFDBFE;">${m.rating || 'Rating B'}</span></td>
          <td>R$ ${m.rv_prevista.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</td>
          <td><span class="badge-status status-${m.status.toLowerCase()}">${m.status}</span></td>
        </tr>
      `).join('');

    } catch (err) {
      console.error('Error loading supervisor dashboard:', err);
    }
  },

  // --- ADMIN PANEL ---
  switchAdminTab(tabName) {
    const tabs = ['visao', 'atualizar', 'feedbacks', 'treinamentos', 'historico', 'colaboradores', 'campanhas'];
    tabs.forEach(t => {
      const btn = document.getElementById(`btnAdminTab${t.charAt(0).toUpperCase() + t.slice(1)}`) || document.querySelector(`.tab-btn[onclick*="${t}"]`);
      const sec = document.getElementById(`tabAdmin${t.charAt(0).toUpperCase() + t.slice(1)}`);
      if (btn) btn.classList.toggle('active', t === tabName);
      if (sec) sec.style.display = (t === tabName) ? 'block' : 'none';
    });

    if (tabName === 'visao') this.loadManagerialOverview();
    if (tabName === 'feedbacks') this.loadAdminFeedbacks();
    if (tabName === 'treinamentos') this.loadAdminTrainings();
    if (tabName === 'historico') this.loadImportHistory();
    if (tabName === 'colaboradores') this.loadAdminCollaborators();
    if (tabName === 'campanhas') this.loadAdminCampaigns();
  },

  loadAdminDashboard() {
    this.switchAdminTab('visao');
  },

  async loadManagerialOverview(competencia = null) {
    try {
      let url = '/api/admin/managerial-overview';
      if (competencia) url += `?competencia=${encodeURIComponent(competencia)}`;

      const res = await fetch(url, { headers: this.getAuthHeaders() });
      if (!res.ok) return;

      const data = await res.json();
      
      if (data.admin_name) {
        document.getElementById('adminGreetingName').textContent = `Visão Gerencial Executiva • ${data.admin_name}`;
      }

      document.getElementById('valVisaoTotalCollabs').textContent = data.total_collabs;
      document.getElementById('valVisaoAvgPerf').textContent = `${data.avg_perf}%`;
      document.getElementById('valVisaoTotalRv').textContent = `R$ ${data.total_rv.toLocaleString('pt-BR', {minimumFractionDigits: 2})}`;
      document.getElementById('valVisaoOpenPlans').textContent = data.open_plans_count;
      document.getElementById('subVisaoTotalPlans').textContent = `${data.plans_count} planos criados no total`;
      document.getElementById('badgeVisaoAtRisk').textContent = `${data.at_risk_collaborators.length} EM RISCO / FORA DA META`;

      // Operational KPI Cards
      document.getElementById('valVisaoAvgDevolucao').textContent = `${(data.avg_devolucao || 0.0).toFixed(2)}%`;
      document.getElementById('valVisaoAvgRaio').textContent = `${(data.avg_raio || 100.0).toFixed(1)}%`;
      document.getElementById('valVisaoTotalCaixas').textContent = `${(data.total_caixas || 0.0).toLocaleString('pt-BR')} cx`;
      document.getElementById('valVisaoTotalMapas').textContent = (data.total_mapas || 0).toLocaleString('pt-BR');
      document.getElementById('valVisaoTotalEntregas').textContent = (data.total_entregas || 0).toLocaleString('pt-BR');
      document.getElementById('valVisaoAvgReposicao').textContent = `${(data.avg_reposicao_pct || 0.0).toFixed(1)}%`;

      // Populate Competencia Selector
      const sel = document.getElementById('selectCompetenciaVisao');
      if (data.available_competencias && data.available_competencias.length > 0) {
        sel.innerHTML = data.available_competencias.map(c => `<option value="${c}" ${c === data.competencia ? 'selected' : ''}>${c}</option>`).join('');
      }

      // Render Collaborators at Risk table
      const tbodyAtRisk = document.getElementById('tbodyVisaoAtRisk');
      if (!data.at_risk_collaborators || data.at_risk_collaborators.length === 0) {
        tbodyAtRisk.innerHTML = '<tr><td colspan="7" style="text-align:center; color:#059669; font-weight:700; padding: 1.5rem;">🎉 Todos os colaboradores atingiram a meta de performance (≥ 90%)!</td></tr>';
      } else {
        tbodyAtRisk.innerHTML = data.at_risk_collaborators.map(c => `
          <tr>
            <td><strong>${c.nome}</strong></td>
            <td><span class="badge-status status-cinza">${c.role}</span></td>
            <td><strong style="color: ${c.performance_pct < 75 ? '#DC2626' : '#D97706'}; font-size: 1rem;">${c.performance_pct}%</strong></td>
            <td><span class="badge-status status-amarelo">${c.rating || 'Rating C'}</span></td>
            <td>${c.devolucao_val}</td>
            <td>${c.banco_horas_val}</td>
            <td>
              <button class="btn-primary" style="font-size:0.75rem; padding:0.3rem 0.6rem;" onclick="app.openNewActionPlanModal(${c.id}, '${c.nome.replace(/'/g, "\\'")}')">
                🎯 Criar Plano de Ação
              </button>
            </td>
          </tr>
        `).join('');
      }

      // Render Full Collaborators Matrix table
      const tbodyAll = document.getElementById('tbodyVisaoAllCollabs');
      document.getElementById('badgeVisaoTotalCount').textContent = `${(data.all_collaborators || []).length} COLABORADORES`;
      if (!data.all_collaborators || data.all_collaborators.length === 0) {
        tbodyAll.innerHTML = '<tr><td colspan="13" style="text-align:center; color:var(--text-muted); padding: 1.5rem;">Nenhum colaborador encontrado nesta competência.</td></tr>';
      } else {
        tbodyAll.innerHTML = data.all_collaborators.map(c => {
          const perfColor = c.performance_pct >= 90 ? '#059669' : (c.performance_pct >= 75 ? '#D97706' : '#DC2626');
          return `
            <tr>
              <td><strong>${c.nome}</strong></td>
              <td><span class="badge-status status-cinza">${c.role}</span></td>
              <td><strong style="color: ${perfColor}; font-size: 0.95rem;">${c.performance_pct}%</strong></td>
              <td><span class="badge-status status-verde">${c.rating}</span></td>
              <td>R$ ${c.rv_prevista.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</td>
              <td>${c.caixas_val.toLocaleString('pt-BR')} cx</td>
              <td>${c.devolucao_val}</td>
              <td>${c.aderencia_raio_val}</td>
              <td>${c.banco_horas_val}</td>
              <td>${c.mapas}</td>
              <td>${c.entregas}</td>
              <td>${c.reposicao_pct}</td>
              <td>
                <button class="btn-primary" style="font-size:0.7rem; padding:0.25rem 0.5rem;" onclick="app.openNewActionPlanModal(${c.id}, '${c.nome.replace(/'/g, "\\'")}')">
                  + Plano
                </button>
              </td>
            </tr>
          `;
        }).join('');
      }

      // Load registered Action Plans
      this.loadActionPlans(data.competencia);
    } catch (err) {
      console.error('Error loading managerial overview:', err);
    }
  },

  async loadActionPlans(competencia = null) {
    try {
      let url = '/api/admin/action-plans';
      if (competencia) url += `?competencia=${encodeURIComponent(competencia)}`;

      const res = await fetch(url, { headers: this.getAuthHeaders() });
      if (!res.ok) return;

      const plans = await res.json();
      const tbody = document.getElementById('tbodyActionPlans');

      if (!plans || plans.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; color:var(--text-muted); padding: 1.5rem;">Nenhum Plano de Ação registrado para esta competência.</td></tr>';
        return;
      }

      tbody.innerHTML = plans.map(p => {
        const statusClass = p.status === 'Concluído' ? 'status-verde' : (p.status === 'Em Acompanhamento' ? 'status-amarelo' : 'status-vermelho');
        return `
          <tr>
            <td><small>${p.created_at}</small></td>
            <td><strong>${p.collaborator_name}</strong> <small style="color:var(--text-muted);">(${p.role})</small></td>
            <td><small>${p.issue_description}</small></td>
            <td><strong>${p.action_title}</strong></td>
            <td><small>${p.corrective_measure}</small></td>
            <td><span class="badge-status status-cinza">${p.deadline}</span></td>
            <td><small>${p.responsible_name}</small></td>
            <td><span class="badge-status ${statusClass}">${p.status}</span></td>
            <td>
              <select style="font-size:0.75rem; padding:0.2rem;" onchange="app.updateActionPlanStatus(${p.id}, this.value)">
                <option value="Pendente" ${p.status === 'Pendente' ? 'selected' : ''}>⏳ Pendente</option>
                <option value="Em Acompanhamento" ${p.status === 'Em Acompanhamento' ? 'selected' : ''}>🔍 Em Acompanhamento</option>
                <option value="Concluído" ${p.status === 'Concluído' ? 'selected' : ''}>✅ Concluído</option>
              </select>
            </td>
          </tr>
        `;
      }).join('');
    } catch (err) {
      console.error('Error loading action plans:', err);
    }
  },

  async openNewActionPlanModal(targetUserId = null, targetUserName = null) {
    try {
      const res = await fetch('/api/admin/collaborators', { headers: this.getAuthHeaders() });
      if (!res.ok) return;

      const users = await res.json();
      const sel = document.getElementById('modalPlanUserId');
      sel.innerHTML = users.map(u => `<option value="${u.id}" ${u.id === targetUserId ? 'selected' : ''}>${u.name} (${u.role})</option>`).join('');

      document.getElementById('formActionPlan').reset();
      document.getElementById('planModalMsg').style.display = 'none';
      
      const deadlineInput = document.getElementById('modalPlanDeadline');
      const today = new Date();
      today.setDate(today.getDate() + 15);
      deadlineInput.value = today.toISOString().split('T')[0];

      document.getElementById('modalActionPlan').style.display = 'flex';
    } catch (err) {
      console.error('Error opening action plan modal:', err);
    }
  },

  closeActionPlanModal() {
    document.getElementById('modalActionPlan').style.display = 'none';
  },

  async submitActionPlan(e) {
    e.preventDefault();
    const userId = parseInt(document.getElementById('modalPlanUserId').value);
    const issue = document.getElementById('modalPlanIssue').value;
    const title = document.getElementById('modalPlanTitle').value;
    const measure = document.getElementById('modalPlanMeasure').value;
    const deadline = document.getElementById('modalPlanDeadline').value;
    const competencia = document.getElementById('selectCompetenciaVisao').value || 'Julho/2026';
    const msgEl = document.getElementById('planModalMsg');

    try {
      const res = await fetch('/api/admin/action-plans', {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({
          user_id: userId,
          competencia: competencia,
          issue_description: issue,
          action_title: title,
          corrective_measure: measure,
          deadline: deadline
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Falha ao salvar Plano de Ação.');
      }

      msgEl.style.background = '#ECFDF5';
      msgEl.style.color = '#065F46';
      msgEl.textContent = 'Plano de Ação registrado com sucesso!';
      msgEl.style.display = 'block';

      setTimeout(() => {
        this.closeActionPlanModal();
        this.loadManagerialOverview(competencia);
      }, 1000);
    } catch (err) {
      msgEl.style.background = '#FEE2E2';
      msgEl.style.color = '#991B1B';
      msgEl.textContent = err.message;
      msgEl.style.display = 'block';
    }
  },

  async updateActionPlanStatus(planId, statusVal) {
    try {
      const formData = new FormData();
      formData.append('status_val', statusVal);

      const res = await fetch(`/api/admin/action-plans/${planId}/status`, {
        method: 'PUT',
        headers: { 'Authorization': `Bearer ${this.token}` },
        body: formData
      });

      if (res.ok) {
        const competencia = document.getElementById('selectCompetenciaVisao').value || 'Julho/2026';
        this.loadManagerialOverview(competencia);
      }
    } catch (err) {
      console.error('Error updating action plan status:', err);
    }
  },

  async loadAdminFeedbacks() {
    try {
      const statusFilter = document.getElementById('adminFilterFeedbackStatus').value || 'Todos';
      const categoryFilter = document.getElementById('adminFilterFeedbackCategory').value || 'Todas';

      let url = `/api/feedback/all?status_filter=${encodeURIComponent(statusFilter)}&category_filter=${encodeURIComponent(categoryFilter)}`;

      const res = await fetch(url, { headers: this.getAuthHeaders() });
      if (!res.ok) return;

      const list = await res.json();
      const tbody = document.getElementById('tbodyAdminFeedbacks');

      if (!list || list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; color:var(--text-muted);">Nenhum feedback encontrado com os filtros selecionados.</td></tr>';
        return;
      }

      this.currentAdminFeedbacks = list;

      tbody.innerHTML = list.map(fb => {
        const statusClass = fb.status === 'RESOLVIDO' ? 'status-verde' : (fb.status === 'EM ANÁLISE' ? 'status-amarelo' : 'status-vermelho');

        return `
          <tr>
            <td><small>${fb.created_at}</small></td>
            <td><strong>${fb.user_name}</strong><br><small style="color:var(--text-muted);">Mat: ${fb.matricula}</small></td>
            <td>${fb.user_role}</td>
            <td><strong>${fb.incident_date}</strong></td>
            <td><span style="font-size:0.75rem; font-weight:600; background:#F1F5F9; padding:0.2rem 0.4rem; border-radius:4px;">${fb.category}</span></td>
            <td style="max-width:280px; font-size:0.85rem;">
              "${fb.comment}"
              ${fb.admin_notes ? `<br><small style="color:#047857; font-weight:600;">Resposta: ${fb.admin_notes}</small>` : ''}
            </td>
            <td><span class="badge-status ${statusClass}">${fb.status}</span></td>
            <td>
              <button class="btn-primary" style="padding:0.35rem 0.6rem; font-size:0.75rem;" onclick="app.openFeedbackActionModal(${fb.id})">TRATAR</button>
            </td>
          </tr>
        `;
      }).join('');

    } catch (err) {
      console.error('Error loading admin feedbacks:', err);
    }
  },

  openFeedbackActionModal(feedbackId) {
    const list = this.currentAdminFeedbacks || [];
    const fb = list.find(item => item.id === feedbackId);
    if (!fb) return;

    document.getElementById('modalFeedbackId').value = fb.id;
    document.getElementById('modalFbCollabName').textContent = `Colaborador: ${fb.user_name} (${fb.user_role} - Matrícula ${fb.matricula})`;
    document.getElementById('modalFbComment').textContent = `"${fb.comment}"`;
    document.getElementById('modalSelectFeedbackStatus').value = fb.status;
    document.getElementById('modalTextareaAdminNotes').value = fb.admin_notes || '';

    document.getElementById('modalFeedbackAction').classList.add('active');
  },

  closeFeedbackActionModal() {
    document.getElementById('modalFeedbackAction').classList.remove('active');
  },

  async submitFeedbackStatusUpdate() {
    const feedbackId = document.getElementById('modalFeedbackId').value;
    const statusVal = document.getElementById('modalSelectFeedbackStatus').value;
    const adminNotes = document.getElementById('modalTextareaAdminNotes').value;

    if (!feedbackId) return;

    try {
      const res = await fetch(`/api/feedback/${feedbackId}/status`, {
        method: 'PUT',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({
          status: statusVal,
          admin_notes: adminNotes.trim()
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Erro ao atualizar feedback.');

      alert('✅ Status do feedback atualizado com sucesso!');
      this.closeFeedbackActionModal();
      this.loadAdminFeedbacks();

    } catch (err) {
      alert(`Erro: ${err.message}`);
    }
  },

  handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
      this.selectedFile = file;
      document.getElementById('fileNameText').textContent = `📄 ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
      document.getElementById('fileSelectedInfo').style.display = 'block';
    }
  },

  async analyzeExcelFile() {
    if (!this.selectedFile) return;

    const btn = document.querySelector('button[onclick="app.analyzeExcelFile()"]');
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'ANALISANDO PLANILHA...';
    }

    try {
      const competencia = document.getElementById('adminSelectCompetencia').value;
      let fileToSend = this.selectedFile;

      // Automatic client-side compression and sheet filtering for large Excel files (> 2.5 MB)
      if (fileToSend.size > 2.5 * 1024 * 1024 && window.XLSX) {
        try {
          btn.textContent = 'COMPRIMINDO E OTIMIZANDO PLANILHA NO NAVEGADOR...';
          const arrayBuffer = await fileToSend.arrayBuffer();
          const wb = XLSX.read(arrayBuffer, { type: 'array', cellStyles: false, cellHTML: false, cellImages: false });
          
          let targetWb = wb;
          const targetKeywords = ['base mot', 'base aju', 'consolidado rv mot', 'consolidado rv aju', 'mot', 'aju', 'base', 'consolidado'];
          const matchedSheets = wb.SheetNames.filter(name => targetKeywords.some(kw => name.toLowerCase().includes(kw)));
          
          if (matchedSheets.length > 0 && matchedSheets.length < wb.SheetNames.length) {
            const newWb = XLSX.utils.book_new();
            matchedSheets.forEach(name => XLSX.utils.book_append_sheet(newWb, wb.Sheets[name], name));
            targetWb = newWb;
          }

          const outArray = XLSX.write(targetWb, { bookType: 'xlsx', type: 'array', compression: true });
          fileToSend = new File([outArray], fileToSend.name, { type: fileToSend.type });
          console.log(`Planilha comprimida de ${(this.selectedFile.size / (1024 * 1024)).toFixed(1)} MB para ${(fileToSend.size / (1024 * 1024)).toFixed(1)} MB!`);
        } catch (optErr) {
          console.warn('Falha ao comprimir planilha no navegador:', optErr);
        }
      }

      btn.textContent = 'ENVIANDO PARA O SERVIDOR...';

      const formData = new FormData();
      formData.append('file', fileToSend);
      formData.append('competencia', competencia);

      const res = await fetch('/api/admin/import/preview', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${this.token}` },
        body: formData
      });

      let data = {};
      const contentType = res.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        data = await res.json();
      } else {
        const text = await res.text();
        if (res.status === 413 || text.includes('Request Entity Too Large') || text.includes('FUNCTION_INVOCATION_FAILED')) {
          throw new Error(`A planilha "${this.selectedFile.name}" possui ${(this.selectedFile.size / (1024 * 1024)).toFixed(1)} MB, excedendo o limite da Vercel (máximo 4.5 MB).\n\nPara importar:\n1. Abra a planilha e salve uma cópia rápida contendo apenas as abas principais (Consolidado RV MOT, Consolidado RV AJU, Base Mot, Base Aju).\n2. Ou remova abas de gráficos/dados brutos extras.`);
        }
        throw new Error(`Erro no servidor (${res.status}): ${text.substring(0, 120)}`);
      }

      if (!res.ok) {
        throw new Error(data.detail || 'Erro ao analisar a planilha.');
      }

      // Populate Preview Modal
      this.currentPreviewToken = data.file_token;

      document.getElementById('prevComp').textContent = data.competencia;
      document.getElementById('prevMotCount').textContent = data.mot_found;
      document.getElementById('prevAjuCount').textContent = data.aju_found;
      document.getElementById('prevValidCount').textContent = data.valid_count;
      document.getElementById('prevErrCount').textContent = data.error_count;

      // Handle Errors List
      const errBox = document.getElementById('prevErrorsBox');
      const errList = document.getElementById('listPrevErrors');
      if (data.errors && data.errors.length > 0) {
        errList.innerHTML = data.errors.map(e => `<li><strong>${e.aba}</strong> - ${e.colaborador}: ${e.problema}</li>`).join('');
        errBox.style.display = 'block';
      } else {
        errBox.style.display = 'none';
      }

      // Populate Sample Table
      const tbody = document.getElementById('tbodyPreviewSample');
      tbody.innerHTML = data.sample.map(s => `
        <tr>
          <td>${s.matricula}</td>
          <td><strong>${s.nome}</strong></td>
          <td>${s.cargo}</td>
          <td>${s.performance_pct.toFixed(1)}%</td>
          <td><span style="font-weight:700; color:#0047BA; background:#EFF6FF; padding:0.15rem 0.4rem; border-radius:4px;">${s.rating || 'Rating B'}</span></td>
          <td>R$ ${s.rv_prevista.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</td>
          <td><span class="badge-status status-${s.status.toLowerCase()}">${s.status}</span></td>
        </tr>
      `).join('');

      // Open Modal
      document.getElementById('modalPreview').classList.add('active');

    } catch (err) {
      alert(`Erro: ${err.message}`);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = 'ANALISAR PLANILHA';
      }
    }
  },

  closePreviewModal() {
    document.getElementById('modalPreview').classList.remove('active');
  },

  async confirmImportAction() {
    if (!this.currentPreviewToken) return;

    const competencia = document.getElementById('adminSelectCompetencia').value;
    const btn = document.getElementById('btnConfirmImport');
    btn.disabled = true;
    btn.textContent = 'GRAVANDO DADOS...';

    try {
      const res = await fetch('/api/admin/import/confirm', {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({
          file_token: this.currentPreviewToken,
          competencia: competencia
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Erro ao confirmar importação.');

      alert(`✅ ${data.message}\nTotal de registros processados: ${data.total_processed}`);
      this.closePreviewModal();

      // Reset file input
      this.selectedFile = null;
      document.getElementById('fileSelectedInfo').style.display = 'none';

      // Switch to history tab
      this.switchAdminTab('historico');

    } catch (err) {
      alert(`Erro ao gravar no banco: ${err.message}`);
    } finally {
      btn.disabled = false;
      btn.textContent = 'CONFIRMAR ATUALIZAÇÃO';
    }
  },

  async loadImportHistory() {
    try {
      const res = await fetch('/api/admin/import/history', { headers: this.getAuthHeaders() });
      if (!res.ok) return;
      const history = await res.json();

      const tbody = document.getElementById('tbodyImportHistory');
      if (!history || history.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; color:var(--text-muted);">Nenhuma importação realizada ainda.</td></tr>';
        return;
      }

      tbody.innerHTML = history.map(h => `
        <tr>
          <td>${h.created_at}</td>
          <td><strong>${h.filename}</strong></td>
          <td><span class="badge-status status-verde">${h.competencia}</span></td>
          <td>${h.total_records}</td>
          <td>${h.mot_count}</td>
          <td>${h.aju_count}</td>
          <td>${h.created_count}</td>
          <td>${h.updated_count}</td>
          <td>${h.imported_by_name}</td>
        </tr>
      `).join('');

    } catch (err) {
      console.error('Error loading import history:', err);
    }
  },

  async loadAdminCollaborators() {
    try {
      const res = await fetch('/api/admin/collaborators', { headers: this.getAuthHeaders() });
      if (!res.ok) return;
      const users = await res.json();
      this.currentAdminUsers = users;

      const tbody = document.getElementById('tbodyAdminUsers');
      tbody.innerHTML = users.map(u => `
        <tr>
          <td>${u.matricula || '-'}</td>
          <td><strong>${u.name}</strong></td>
          <td>${u.role}</td>
          <td><code>${u.masked_cpf}</code></td>
          <td><span class="badge-status status-${(u.status === 'Ativo' ? 'verde' : 'vermelho')}">${u.status}</span></td>
          <td>
            <div style="display: flex; gap: 0.5rem;">
              <button class="btn-primary" style="font-size: 0.75rem; padding: 0.25rem 0.5rem;" onclick="app.openEditUserModal(${u.id})">✏️ Editar</button>
              <button class="btn-logout" style="font-size: 0.75rem; padding: 0.25rem 0.5rem; background: #FEF2F2; color: #DC2626; border: 1px solid #FCA5A5;" onclick="app.deleteCollaborator(${u.id}, '${u.name}')">❌ Desativar</button>
            </div>
          </td>
        </tr>
      `).join('');
    } catch (err) {
      console.error('Error loading admin collaborators:', err);
    }
  },

  openCreateUserModal() {
    document.getElementById('modalUserId').value = '';
    document.getElementById('modalUserTitle').textContent = 'Cadastrar Novo Colaborador';
    document.getElementById('modalUserNome').value = '';
    document.getElementById('modalUserMatricula').value = '';
    document.getElementById('modalUserCpf').value = '';
    document.getElementById('modalUserRole').value = 'MOTORISTA';
    document.getElementById('modalUserPassword').value = '123';
    document.getElementById('modalUserStatus').value = 'Ativo';
    document.getElementById('userModalMsg').style.display = 'none';

    document.getElementById('modalCreateUser').classList.add('active');
  },

  openEditUserModal(userId) {
    const list = this.currentAdminUsers || [];
    const u = list.find(item => item.id === userId);
    if (!u) return;

    document.getElementById('modalUserId').value = u.id;
    document.getElementById('modalUserTitle').textContent = `Editar Colaborador: ${u.name}`;
    document.getElementById('modalUserNome').value = u.name;
    document.getElementById('modalUserMatricula').value = u.matricula || '';
    document.getElementById('modalUserCpf').value = u.masked_cpf || '';
    document.getElementById('modalUserRole').value = u.role;
    document.getElementById('modalUserPassword').value = '';
    document.getElementById('modalUserStatus').value = u.status || 'Ativo';
    document.getElementById('userModalMsg').style.display = 'none';

    document.getElementById('modalCreateUser').classList.add('active');
  },

  closeCreateUserModal() {
    document.getElementById('modalCreateUser').classList.remove('active');
  },

  async submitUserModal(e) {
    e.preventDefault();
    const userId = document.getElementById('modalUserId').value;
    const nome = document.getElementById('modalUserNome').value.trim();
    const matricula = document.getElementById('modalUserMatricula').value.trim();
    const cpf = document.getElementById('modalUserCpf').value.trim();
    const role = document.getElementById('modalUserRole').value;
    const password = document.getElementById('modalUserPassword').value;
    const statusVal = document.getElementById('modalUserStatus').value;

    const msgEl = document.getElementById('userModalMsg');
    const btn = document.getElementById('btnSubmitUserModal');
    btn.disabled = true;

    try {
      const isEdit = !!userId;
      const url = isEdit ? `/api/admin/collaborators/${userId}` : '/api/admin/collaborators';
      const method = isEdit ? 'PUT' : 'POST';

      const body = {
        name: nome,
        matricula: matricula,
        role: role,
        status: statusVal
      };
      if (cpf && !cpf.includes('*')) body.cpf = cpf;
      if (password) body.password = password;

      const res = await fetch(url, {
        method: method,
        headers: this.getAuthHeaders(),
        body: JSON.stringify(body)
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Erro ao salvar colaborador.');

      alert(`✅ Colaborador ${isEdit ? 'atualizado' : 'cadastrado'} com sucesso!`);
      this.closeCreateUserModal();
      this.loadAdminCollaborators();

    } catch (err) {
      msgEl.style.display = 'block';
      msgEl.style.background = '#FEF2F2';
      msgEl.style.color = '#991B1B';
      msgEl.textContent = err.message;
    } finally {
      btn.disabled = false;
    }
  },

  async deleteCollaborator(userId, userName) {
    if (!confirm(`Deseja realmente desativar o colaborador ${userName}?`)) return;

    try {
      const res = await fetch(`/api/admin/collaborators/${userId}`, {
        method: 'DELETE',
        headers: this.getAuthHeaders()
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Erro ao desativar colaborador.');

      alert(`✅ Colaborador desativado com sucesso!`);
      this.loadAdminCollaborators();

    } catch (err) {
      alert(`Erro: ${err.message}`);
    }
  },

  async loadAdminCampaigns() {
    try {
      const res = await fetch('/api/campaigns', { headers: this.getAuthHeaders() });
      if (!res.ok) return;
      const campaigns = await res.json();

      const container = document.getElementById('adminCampaignsList');
      container.innerHTML = campaigns.map(c => `
        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; padding: 1rem; border-radius: 10px; margin-bottom: 1rem;">
          <div style="display:flex; justify-content:space-between; font-weight:700;">
            <span>${c.title}</span>
            <span class="badge-status status-verde">${c.status}</span>
          </div>
          <div style="font-size:0.85rem; color:var(--text-muted); margin-top:0.3rem;">
            Meta: ${c.goal} | Prêmio: ${c.prize}
          </div>
        </div>
      `).join('');
    } catch (err) {
      console.error('Error loading admin campaigns:', err);
    }
  }
};

// Initialize app on DOM ready
document.addEventListener('DOMContentLoaded', () => app.init());
