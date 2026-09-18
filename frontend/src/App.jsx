import { useState } from "react";
import "./App.css";

function App() {
  const [url, setUrl] = useState("");
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState(null);

  const handleScan = () => {
    if (!url.trim()) {
      alert("Please enter a website URL");
      return;
    }

    setScanning(true);
    setResult(null);

    // Temporary mock scan
    setTimeout(() => {
      setResult({
        url: url,
        title: "Example Website",
        patterns: [
          {
            type: "Urgency",
            description: "Limited time message detected."
          },
          {
            type: "Scarcity",
            description: "Limited availability message detected."
          },
          {
            type: "Forced Action",
            description: "User is encouraged to take an unnecessary action."
          }
        ]
      });

      setScanning(false);
    }, 1500);
  };

  return (
    <div className="app">
      <header className="hero">
        <div className="shield">🛡️</div>

        <h1>DarkShield AI</h1>

        <p>AI-Powered Dark Pattern Detection</p>
      </header>

      <main className="container">
        <section className="scan-box">
          <label>Enter Website URL</label>

          <div className="input-row">
            <input
              type="url"
              placeholder="https://example.com"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />

            <button onClick={handleScan} disabled={scanning}>
              {scanning ? "Scanning..." : "Scan Website"}
            </button>
          </div>

          {scanning && (
            <div className="loading">
              🔍 Scanning website...
              <br />
              Please wait
            </div>
          )}
        </section>

        {result && (
          <section className="results">
            <h2>Scan Results</h2>

            <div className="website-info">
              <p>
                <strong>Website:</strong> {result.url}
              </p>

              <p>
                <strong>Title:</strong> {result.title}
              </p>
            </div>

            <h3>Dark Patterns Detected</h3>

            <div className="patterns">
              {result.patterns.map((pattern, index) => (
                <div className="pattern-card" key={index}>
                  <h4>⚠️ {pattern.type}</h4>
                  <p>{pattern.description}</p>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;