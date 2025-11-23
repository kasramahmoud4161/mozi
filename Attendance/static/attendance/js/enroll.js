// static/attendance/js/enroll.js
(async function () {
  const video = document.getElementById('video');
  const startBtn = document.getElementById('start');
  const capBtn = document.getElementById('capture');
  const status = document.getElementById('status');

  startBtn.addEventListener('click', async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 1280 }, audio: false });
      video.srcObject = stream;
      await video.play();
      status.innerText = "وب‌کم فعال شد.";
    } catch (e) {
      status.innerText = "خطا در دسترسی به وب‌کم: " + e.message;
    }
  });

  capBtn.addEventListener('click', async () => {
    const idInput = document.getElementById('student_id');
    const student_id = idInput.value.trim();
    if (!student_id) return alert('لطفاً Student ID وارد کن.');

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.9);

    status.innerText = "در حال ارسال تصویر به سرور...";
    try {
      const res = await fetch(`/attendance/enroll/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: student_id, image: dataUrl })
      });
      const j = await res.json();
      if (res.ok && j.status === 'ok') {
        status.innerText = "ثبت شد ✅";
      } else {
        status.innerText = "خطا: " + (j.message || JSON.stringify(j));
      }
    } catch (err) {
      status.innerText = "ارسال ناموفق: " + err.message;
    }
  });
})();
