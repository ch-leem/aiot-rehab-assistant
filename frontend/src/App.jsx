import { useEffect, useState } from "react";

export default function App() {
  const [userHealth, setUserHealth] = useState("loading...");
  const [iotHealth, setIotHealth] = useState("loading...");

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.text())
      .then(setUserHealth)
      .catch(() => setUserHealth("ERROR"));

    fetch("/iot-api/health")
      .then((r) => r.text())
      .then(setIotHealth)
      .catch(() => setIotHealth("ERROR"));
  }, []);

  return (
    <div style={{ padding: 24, fontFamily: "sans-serif" }}>
      <h2>Rehab Dashboard (Vite + React)</h2>
      <p>User API: {userHealth}</p>
      <p>IoT API: {iotHealth}</p>
    </div>
  );
}
