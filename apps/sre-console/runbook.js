// AKS SRE Console — SRE Runbook Copilot (Fixed Guidance, No AI Backend)
// =========================================================================
// Static runbook helper. The public console has no cluster telemetry or AI backend.
// =========================================================================

function toggleSreCopilot() {
  const modal = document.getElementById('sre-copilot-modal');
  const btn = document.getElementById('sre-copilot-btn');
  if (modal.classList.contains('hidden')) {
    modal.classList.remove('hidden');
    btn.classList.add('hidden');
  } else {
    modal.classList.add('hidden');
    btn.classList.remove('hidden');
  }
}

function runbookAnswer(question) {
  const normalized = question.toLocaleLowerCase('vi-VN');
  if (/pdb|drain|gián đoạn|zero downtime/.test(normalized)) {
    return {
      title: 'PDB & node drain',
      text: 'PDB giới hạn số pod bị gián đoạn tự nguyện qua Eviction API; riêng PDB không bảo đảm zero downtime. Kiểm tra số replica, readiness probe, tài nguyên dự phòng và graceful termination. Sau đó chạy diễn tập drain và đo request thành công trong suốt quá trình.',
      source: '/runbooks/incident-response/',
      sourceLabel: 'Runbook ứng phó sự cố'
    };
  }
  if (/networkpolicy|network policy|cni|chặn gói|drop gói/.test(normalized)) {
    return {
      title: 'Xác minh NetworkPolicy',
      text: 'Manifest NetworkPolicy chỉ có hiệu lực khi CNI hỗ trợ thực thi. Hãy xác nhận plugin mạng đang dùng, thử kết nối từ pod được phép và pod bị chặn, rồi lưu kết quả probe. Không thể kết luận gói tin đã bị chặn chỉ từ manifest.',
      source: '/evidence/test-results/',
      sourceLabel: 'Bằng chứng kiểm thử'
    };
  }
  if (/burn|slo|sli|error budget|ngân sách lỗi/.test(normalized)) {
    return {
      title: 'Error budget burn rate',
      text: 'Burn rate = tỷ lệ lỗi quan sát được / tỷ lệ lỗi cho phép theo SLO. Với SLO 99,9% trong 30 ngày, mức tiêu thụ 2% ngân sách lỗi trong 1 giờ tương ứng 0,02 × 720 / 1 = 14,4 lần. Đây là ngưỡng tham khảo; chỉ kết luận có cảnh báo khi có số liệu SLI thực.',
      source: 'https://sre.google/workbook/alerting-on-slos/',
      sourceLabel: 'Google SRE Workbook'
    };
  }
  if (/readiness|dependency|503|probe/.test(normalized)) {
    return {
      title: 'Điều tra readiness và dependency',
      text: 'Kiểm tra readiness endpoint, pod endpoints, sự phụ thuộc và lưu lượng 5xx trước/sau sự cố. Readiness thất bại sẽ làm pod không còn phù hợp nhận lưu lượng Service sau khi trạng thái được cập nhật; cần đo thực tế để xác nhận tác động.',
      source: '/runbooks/incident-response/',
      sourceLabel: 'Runbook ứng phó sự cố'
    };
  }
  return {
    title: 'Chưa có hướng dẫn cho câu hỏi này',
    text: 'Trợ lý này tra cứu các hướng dẫn cố định, không đọc trạng thái cụm và không tạo câu trả lời AI. Hãy thử một trong các chủ đề PDB, NetworkPolicy, burn rate hoặc readiness; với sự cố khác, mở runbook ứng phó.',
    source: '/runbooks/incident-response/',
    sourceLabel: 'Runbook ứng phó sự cố'
  };
}

function sendSreCopilotMessage(presetText) {
  const input = document.getElementById('sre-copilot-input');
  const text = (presetText || input.value).trim();
  if (!text) return;
  input.value = '';

  const container = document.getElementById('sre-copilot-messages');
  const time = new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });

  const userRow = document.createElement('div');
  userRow.className = 'flex justify-end gap-2 text-xs';
  const userBubble = document.createElement('div');
  userBubble.className = 'bg-cyan-600 text-white p-2.5 rounded-2xl rounded-br-none max-w-[85%] leading-relaxed shadow';
  userBubble.textContent = text;
  userRow.appendChild(userBubble);
  container.appendChild(userRow);

  const answer = runbookAnswer(text);
  const answerRow = document.createElement('div');
  answerRow.className = 'flex justify-start gap-2 text-xs';
  const answerBubble = document.createElement('div');
  answerBubble.className = 'bg-gray-900 text-gray-200 border border-gray-800 p-3 rounded-2xl rounded-bl-none max-w-[85%] leading-relaxed shadow-lg';
  const title = document.createElement('div');
  title.className = 'font-bold text-cyan-300 mb-1';
  title.textContent = answer.title;
  const body = document.createElement('p');
  body.className = 'leading-relaxed';
  body.textContent = answer.text;
  const source = document.createElement('a');
  source.className = 'text-cyan-300 underline';
  source.href = answer.source;
  source.textContent = `Nguồn: ${answer.sourceLabel}`;
  const timestamp = document.createElement('div');
  timestamp.className = 'text-[9px] text-gray-500 text-right mt-1.5';
  timestamp.textContent = time;
  answerBubble.append(title, body, source, timestamp);
  answerRow.appendChild(answerBubble);
  container.appendChild(answerRow);
  container.scrollTop = container.scrollHeight;
}

// Export to window for inline onclick handlers
window.toggleSreCopilot = toggleSreCopilot;
window.sendSreCopilotMessage = sendSreCopilotMessage;
