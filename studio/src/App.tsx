import "./App.css";

function App() {
  return (
    <div className="shell">
      <header className="shell-header">
        <span className="wordmark">DISPATCH</span>
        <span className="eyebrow">Strategy Studio</span>
      </header>
      <main className="shell-main">
        <section className="panel control-panel" aria-label="Control panel"></section>
        <section className="panel results-panel" aria-label="Recommended plan"></section>
        <section className="panel headline-panel" aria-label="Headline metric"></section>
      </main>
    </div>
  );
}

export default App;
