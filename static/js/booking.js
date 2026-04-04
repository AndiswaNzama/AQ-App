(function () {
  'use strict';

  // ── State ──
  const state = {
    serviceId: null,
    serviceName: '',
    servicePrice: '',
    hour: null,
    slotDate: '',
    slotTime: '',
    calendar: null,
    availableDates: [],
  };

  // ── DOM refs ──
  const steps = [null,
    document.getElementById('step-1'),
    document.getElementById('step-2'),
    document.getElementById('step-3'),
    document.getElementById('step-4'),
  ];
  const stepInds = [null,
    document.getElementById('step-ind-1'),
    document.getElementById('step-ind-2'),
    document.getElementById('step-ind-3'),
    document.getElementById('step-ind-4'),
  ];

  function showStep(n) {
    steps.forEach((s, i) => { if (s) s.classList.toggle('hidden', i !== n); });
    stepInds.forEach((s, i) => {
      if (!s) return;
      s.classList.remove('active', 'done');
      if (i < n) s.classList.add('done');
      else if (i === n) s.classList.add('active');
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // ── Step 1: Service selection ──
  const serviceCards = document.querySelectorAll('.service-card.selectable');
  const nextStep1Btn = document.getElementById('next-step-1');

  if (window.SELECTED_SERVICE_ID) {
    const preCard = document.querySelector(`.service-card.selectable[data-id="${window.SELECTED_SERVICE_ID}"]`);
    if (preCard) selectService(preCard);
  }

  serviceCards.forEach(card => card.addEventListener('click', () => selectService(card)));

  function selectService(card) {
    serviceCards.forEach(c => c.classList.remove('selected'));
    card.classList.add('selected');
    card.querySelector('input[type="radio"]').checked = true;
    state.serviceId = parseInt(card.dataset.id);
    state.serviceName = card.querySelector('h3').textContent;
    state.servicePrice = card.querySelector('.service-price').textContent;
    nextStep1Btn.disabled = false;
  }

  nextStep1Btn.addEventListener('click', () => {
    if (!state.serviceId) return;
    showStep(2);
    initCalendar();
  });

  // ── Step 2: Calendar ──
  async function initCalendar() {
    if (state.calendar) return;

    const res = await fetch('/booking/available-dates');
    state.availableDates = await res.json();

    const calEl = document.getElementById('calendar');
    state.calendar = new FullCalendar.Calendar(calEl, {
      initialView: 'dayGridMonth',
      headerToolbar: { left: 'prev', center: 'title', right: 'next' },
      height: 'auto',
      // Mark available dates with events (dots) so they're visually obvious
      events: state.availableDates.map(d => ({
        start: d,
        display: 'background',
        color: 'rgba(201,168,76,0.25)',
      })),
      dayCellDidMount: (info) => {
        const d = info.date.toISOString().split('T')[0];
        if (state.availableDates.includes(d)) {
          info.el.style.cursor = 'pointer';
          info.el.style.borderBottom = '2px solid #c9a84c';
          // Click on the whole cell, not just the number
          info.el.addEventListener('click', () => loadSlots(d));
        }
      },
    });
    state.calendar.render();
  }

  async function loadSlots(dateStr) {
    const label = document.getElementById('slot-date-label');
    label.textContent = new Date(dateStr + 'T00:00').toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
    const slotList = document.getElementById('slot-list');
    slotList.innerHTML = '<p style="color:var(--text-muted);font-size:.85rem">Loading…</p>';

    const res = await fetch(`/booking/available-slots?date=${dateStr}&service_id=${state.serviceId}`);
    const data = await res.json();

    slotList.innerHTML = '';
    state.hour = null;
    state.slotDate = dateStr;
    document.getElementById('next-step-2').disabled = true;

    // Full-day service
    if (data.full_day !== undefined) {
      if (!data.available) {
        slotList.innerHTML = '<p style="color:var(--text-muted);font-size:.85rem">This date is fully booked. Please choose another.</p>';
        return;
      }
      slotList.innerHTML = `
        <div style="background:rgba(201,168,76,.1);border:1px solid var(--accent);border-radius:8px;padding:1rem;text-align:center">
          <p style="color:var(--accent);font-weight:600;margin-bottom:.25rem">Full Day Coverage</p>
          <p style="color:var(--text-muted);font-size:.85rem">9:00 AM – 12:00 AM (full day)</p>
        </div>`;
      state.slotTime = 'Full Day (9:00 AM – 12:00 AM)';
      state.hour = 'fullday';
      document.getElementById('next-step-2').disabled = false;
      return;
    }

    // Hourly service
    if (!data.length) {
      slotList.innerHTML = '<p style="color:var(--text-muted);font-size:.85rem">No slots available for this date.</p>';
      return;
    }

    const select = document.createElement('select');
    select.className = 'slot-select';
    select.innerHTML = '<option value="">-- Select a time --</option>';

    data.forEach(slot => {
      const opt = document.createElement('option');
      opt.value = slot.hour;
      opt.dataset.start = slot.start;
      opt.dataset.end = slot.end;
      if (slot.booked) {
        opt.disabled = true;
        opt.textContent = `${slot.start} – ${slot.end}  (Booked)`;
        opt.style.color = '#555';
      } else {
        opt.textContent = `${slot.start} – ${slot.end}`;
      }
      select.appendChild(opt);
    });

    select.addEventListener('change', () => {
      const opt = select.options[select.selectedIndex];
      if (!opt.value || opt.disabled) {
        state.hour = null;
        document.getElementById('next-step-2').disabled = true;
        return;
      }
      state.hour = parseInt(opt.value);
      state.slotDate = dateStr;
      state.slotTime = `${opt.dataset.start} – ${opt.dataset.end}`;
      document.getElementById('next-step-2').disabled = false;
    });

    slotList.appendChild(select);
  }

  document.getElementById('back-step-2').addEventListener('click', () => showStep(1));
  document.getElementById('next-step-2').addEventListener('click', () => {
    if (state.hour === null) return;
    showStep(3);
  });

  // ── Step 3: Details ──
  document.getElementById('back-step-3').addEventListener('click', () => showStep(2));
  document.getElementById('next-step-3').addEventListener('click', () => {
    const name = document.getElementById('client_name').value.trim();
    const email = document.getElementById('client_email').value.trim();
    if (!name || !email) {
      alert('Please fill in your name and email.');
      return;
    }
    document.getElementById('r-service').textContent = state.serviceName;
    document.getElementById('r-date').textContent =
      new Date(state.slotDate + 'T00:00').toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
    document.getElementById('r-time').textContent = state.slotTime;
    document.getElementById('r-name').textContent = name;
    document.getElementById('r-email').textContent = email;
    document.getElementById('r-price').textContent = state.servicePrice;
    showStep(4);
  });

  // ── Step 4: Pay ──
  document.getElementById('back-step-4').addEventListener('click', () => showStep(3));
  document.getElementById('pay-btn').addEventListener('click', async () => {
    const payBtn = document.getElementById('pay-btn');
    const errEl = document.getElementById('booking-error');
    payBtn.disabled = true;
    payBtn.textContent = 'Processing…';
    errEl.classList.add('hidden');

    const payload = {
      service_id: state.serviceId,
      date: state.slotDate,
      client_name: document.getElementById('client_name').value.trim(),
      client_email: document.getElementById('client_email').value.trim(),
      client_phone: document.getElementById('client_phone').value.trim(),
      notes: document.getElementById('notes').value.trim(),
    };
    if (state.hour !== 'fullday') payload.hour = state.hour;

    try {
      const res = await fetch('/booking/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Something went wrong. Please try again.');
      window.location.href = data.checkout_url;
    } catch (err) {
      errEl.textContent = err.message;
      errEl.classList.remove('hidden');
      payBtn.disabled = false;
      payBtn.textContent = 'Pay with Card';
    }
  });

  showStep(1);
})();
