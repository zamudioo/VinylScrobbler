//ZamudioScrobbler/frontend/app.js
const screens = {
  idle: document.getElementById("idle"),
  playing: document.getElementById("playing")
};

let currentTrackId = null;

function setScreen(name) {
  Object.values(screens).forEach(s => s.classList.remove("active"));
  screens[name]?.classList.add("active");
}

function updateClock() {
  const now = new Date();

  document.getElementById("clock").innerText =
    now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  document.getElementById("date").innerText =
    now.toLocaleDateString([], {
      weekday: 'long',
      month: 'long',
      day: 'numeric'
    });
}

setInterval(updateClock, 1000);
updateClock();

const ws = new WebSocket("ws://localhost:8000/ws");

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  // 🔇 IDLE → LITE MODE
  if (data.status === "idle") {
    currentTrackId = null;
    document.body.classList.add("lite");
    setScreen("idle");
    return;
  }

  // 🎵 PLAYING
  if (data.status === "playing" && data.track) {
    const newTrackId = `${data.track.artist}-${data.track.title}`;
    if (newTrackId === currentTrackId) return;

    currentTrackId = newTrackId;
    document.body.classList.remove("lite");

    document.getElementById("title").innerText = data.track.title;
    document.getElementById("artist").innerText = data.track.artist;

    if (data.track.cover) {
      document.getElementById("cover").src = data.track.cover;
      document.getElementById("background").style.backgroundImage =
        `url(${data.track.cover})`;
    }

    setScreen("playing");
  }
};

setScreen("idle");
document.body.classList.add("lite");
