import React, { useState } from 'react';
import { Database, Search, GitBranch, Bug, Image, Send, Loader2, CheckCircle2, FolderGit2 } from 'lucide-react';
import { ingestRepo, getDiagram, getGraph, getBugs, askQuestion } from './api';
import mermaid from 'mermaid';

mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
  securityLevel: 'loose',
  fontFamily: 'system-ui, -apple-system, sans-serif'
});

function MermaidChart({ chart }) {
  const chartRef = React.useRef(null);

  React.useEffect(() => {
    if (chartRef.current && chart) {
      const id = `mermaid-${Math.random().toString(36).substring(2, 9)}`;
      mermaid.render(id, chart)
        .then(({ svg }) => {
          chartRef.current.innerHTML = svg;
          const svgElement = chartRef.current.querySelector('svg');
          if (svgElement) {
             svgElement.style.width = '100%';
             svgElement.style.height = 'auto';
             svgElement.style.maxWidth = '100%';
          }
        })
        .catch((error) => {
          console.error("Mermaid parsing failed", error);
          chartRef.current.innerHTML = `<pre style="color:red; background:rgba(255,0,0,0.1); padding:1rem; border-radius:8px;">${error.message || 'Syntax Error'}</pre><pre>${chart}</pre>`;
        });
    }
  }, [chart]);

  return <div ref={chartRef} className="mermaid-chart-container" style={{ width: '100%', minHeight: '400px', display: 'flex', justifyContent: 'center', alignItems: 'center' }} />;
}

function App() {
  const [activeTab, setActiveTab] = useState('ingest');
  const [repoUrl, setRepoUrl] = useState('');
  const [repoName, setRepoName] = useState(localStorage.getItem('repoName') || '');
  const [loading, setLoading] = useState(false);
  const [ingestStatus, setIngestStatus] = useState(null);

  // Q&A State
  const [question, setQuestion] = useState('');
  const [chatHistory, setChatHistory] = useState([]);

  // Diagram & Graph State
  const [diagramData, setDiagramData] = useState(null);
  const [graphData, setGraphData] = useState(null);

  // Bug State
  const [bugsData, setBugsData] = useState(null);

  const handleIngest = async (e) => {
    e.preventDefault();
    setLoading(true);
    setIngestStatus(null);
    try {
      const data = await ingestRepo(repoUrl);
      setIngestStatus({ success: true, message: data.message });
      setRepoName(data.repo_name);
      localStorage.setItem('repoName', data.repo_name);
    } catch (err) {
      setIngestStatus({ success: false, message: err.response?.data?.detail || err.message });
    } finally {
      setLoading(false);
    }
  };

  const handleAsk = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;

    const newHistory = [...chatHistory, { role: 'user', content: question }];
    setChatHistory(newHistory);
    setQuestion('');
    setLoading(true);

    try {
      const data = await askQuestion(repoName, question);
      setChatHistory([...newHistory, { role: 'bot', content: data.answer }]);
    } catch (err) {
      setChatHistory([...newHistory, { role: 'bot', content: `Error: ${err.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  const loadDiagram = async () => {
    setLoading(true);
    try {
      const data = await getDiagram(repoName);
      setDiagramData(data);
    } catch (err) {
      alert("Failed to load diagram: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadGraph = async () => {
    setLoading(true);
    try {
      const data = await getGraph(repoName);
      setGraphData(data);
    } catch (err) {
      alert("Failed to load graph: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadBugs = async () => {
    setLoading(true);
    try {
      const data = await getBugs(repoName);
      setBugsData(data);
    } catch (err) {
      alert("Failed to load bugs: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'ingest':
        return (
          <div className="glass-panel" style={{ maxWidth: '600px', margin: '0 auto', marginTop: '2rem' }}>
            <h2>Ingest Repository</h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>
              Clone and analyze a GitHub repository. This may take a few minutes for large repos.
            </p>
            <form onSubmit={handleIngest} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <input 
                type="url" 
                placeholder="https://github.com/username/repo" 
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                required
              />
              <button type="submit" disabled={loading}>
                {loading ? <Loader2 className="spinner" size={18} /> : <Database size={18} />}
                {loading ? 'Analyzing...' : 'Ingest Repository'}
              </button>
            </form>
            
            {ingestStatus && (
              <div style={{ 
                marginTop: '1.5rem', 
                padding: '1rem', 
                borderRadius: '8px',
                background: ingestStatus.success ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                color: ingestStatus.success ? 'var(--success)' : 'var(--danger)',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem'
              }}>
                {ingestStatus.success && <CheckCircle2 size={18} />}
                {ingestStatus.message}
              </div>
            )}

            {repoName && (
              <div style={{ marginTop: '2rem', padding: '1rem', background: 'rgba(255,255,255,0.05)', borderRadius: '8px' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Currently analyzing: </span>
                <strong>{repoName}</strong>
              </div>
            )}
          </div>
        );

      case 'chat':
        return (
          <div className="glass-panel chat-container">
            <div className="messages">
              {chatHistory.length === 0 && (
                <div style={{ textAlign: 'center', color: 'var(--text-secondary)', marginTop: '2rem' }}>
                  Ask questions about {repoName || 'the repository'}
                </div>
              )}
              {chatHistory.map((msg, idx) => (
                <div key={idx} className={`message ${msg.role}`}>
                  {msg.content}
                </div>
              ))}
              {loading && (
                <div className="message bot" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Loader2 className="spinner" size={16} /> Thinking...
                </div>
              )}
            </div>
            <form className="chat-input" onSubmit={handleAsk}>
              <input 
                type="text" 
                placeholder="How does authentication work?" 
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                disabled={loading || !repoName}
              />
              <button type="submit" disabled={loading || !repoName}>
                <Send size={18} />
              </button>
            </form>
          </div>
        );

      case 'diagram':
        return (
          <div className="glass-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h2>Architecture Diagram</h2>
              <button onClick={loadDiagram} disabled={loading || !repoName}>
                {loading ? <Loader2 className="spinner" size={18} /> : 'Generate Diagram'}
              </button>
            </div>
            {diagramData ? (
              <div style={{ flex: 1, overflowY: 'auto' }}>
                <p style={{ marginBottom: '1rem', lineHeight: '1.6' }}>{diagramData.summary}</p>
                <div style={{ background: 'var(--color-bg)', padding: '1rem', borderRadius: '8px', border: '2px solid var(--color-border)', boxShadow: '4px 4px 0 var(--color-shadow)' }}>
                  <MermaidChart chart={diagramData.mermaid} />
                </div>
              </div>
            ) : (
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
                Click generate to create architecture diagram for {repoName || 'the repository'}
              </div>
            )}
          </div>
        );

      case 'graph':
        return (
          <div className="glass-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h2>Dependency Graph</h2>
              <button onClick={loadGraph} disabled={loading || !repoName}>
                {loading ? <Loader2 className="spinner" size={18} /> : 'Load Graph'}
              </button>
            </div>
            {graphData ? (
              <div style={{ flex: 1, position: 'relative' }}>
                <iframe 
                  srcDoc={graphData.html} 
                  style={{ width: '100%', height: '100%', border: 'none', borderRadius: '8px', background: 'white' }}
                  title="Dependency Graph"
                />
              </div>
            ) : (
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
                Click load to view the dependency graph for {repoName || 'the repository'}
              </div>
            )}
          </div>
        );

      case 'bugs':
        return (
          <div className="glass-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h2>Bug Review</h2>
              <button onClick={loadBugs} disabled={loading || !repoName}>
                {loading ? <Loader2 className="spinner" size={18} /> : 'Scan for Bugs'}
              </button>
            </div>
            {bugsData ? (
              <div style={{ flex: 1, overflowY: 'auto' }}>
                {bugsData.bugs?.map((bug, idx) => (
                  <div key={idx} className="bug-card">
                    <h3>{bug.file} (Line {bug.line})</h3>
                    <p><strong>Severity:</strong> <span style={{ color: 'var(--danger)' }}>{bug.severity}</span></p>
                    <p>{bug.issue}</p>
                    {bug.suggestion && (
                      <div style={{ marginTop: '0.5rem', background: 'rgba(255,255,255,0.05)', padding: '0.5rem', borderRadius: '4px' }}>
                        <strong>Fix:</strong> {bug.suggestion}
                      </div>
                    )}
                  </div>
                ))}
                {!bugsData.bugs?.length && <p>No critical bugs found by the AI.</p>}
              </div>
            ) : (
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
                Click scan to run AI code review on {repoName || 'the repository'}
              </div>
            )}
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="app-container">
      <div className="sidebar">
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          marginBottom: '2.5rem',
          userSelect: 'none'
        }}>
          <div style={{
            background: 'var(--color-accent)',
            padding: '8px',
            borderRadius: '10px',
            border: '2px solid var(--color-border)',
            boxShadow: '3px 3px 0 var(--color-shadow)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transform: 'rotate(-5deg)'
          }}>
            <Database size={24} color="white" strokeWidth={2.5} />
          </div>
          <div style={{
            fontSize: '1.6rem',
            fontWeight: '900',
            letterSpacing: '-0.5px',
            lineHeight: 1,
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            <span style={{ color: 'var(--color-text-strong)' }}>Codebase</span>
            <span style={{ 
              background: 'var(--color-text-strong)', 
              color: 'var(--color-bg)', 
              padding: '2px 8px', 
              borderRadius: '6px',
              border: '2px solid var(--color-border)',
              transform: 'rotate(3deg)',
              display: 'inline-block',
              boxShadow: '2px 2px 0 var(--color-accent)'
            }}>Intel</span>
          </div>
        </div>
        
        <div 
          className={`nav-link ${activeTab === 'ingest' ? 'active' : ''}`}
          onClick={() => setActiveTab('ingest')}
        >
          <Database size={18} /> Ingest Repo
        </div>
        <div 
          className={`nav-link ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => setActiveTab('chat')}
        >
          <Search size={18} /> Semantic Q&A
        </div>
        <div 
          className={`nav-link ${activeTab === 'diagram' ? 'active' : ''}`}
          onClick={() => setActiveTab('diagram')}
        >
          <Image size={18} /> Architecture
        </div>
        <div 
          className={`nav-link ${activeTab === 'graph' ? 'active' : ''}`}
          onClick={() => setActiveTab('graph')}
        >
          <GitBranch size={18} /> Dependency Graph
        </div>
        <div 
          className={`nav-link ${activeTab === 'bugs' ? 'active' : ''}`}
          onClick={() => setActiveTab('bugs')}
        >
          <Bug size={18} /> Code Review
        </div>
      </div>
      
      <div className="main-content">
        <div className="topbar" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          {repoName ? (
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.75rem',
              background: 'var(--color-bg-elevated)',
              color: 'var(--color-text-strong)',
              padding: '0.5rem 1.25rem',
              borderRadius: '999px',
              border: '2px solid var(--color-border)',
              boxShadow: '4px 4px 0 var(--color-shadow)',
              fontWeight: 'bold',
              fontSize: '0.95rem',
              letterSpacing: '0.5px'
            }}>
              <div style={{
                width: '10px',
                height: '10px',
                backgroundColor: 'var(--success)',
                borderRadius: '50%',
                boxShadow: '0 0 5px var(--success)',
                border: '1px solid var(--color-border)'
              }} />
              <FolderGit2 size={18} />
              <span>Active Repo: <span style={{ color: 'var(--color-accent)' }}>{repoName}</span></span>
            </div>
          ) : (
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.75rem',
              background: 'var(--color-bg-elevated)',
              color: 'var(--color-text-muted)',
              padding: '0.5rem 1rem',
              borderRadius: '999px',
              border: '2px dashed var(--color-border-subtle)',
              fontWeight: '600',
              fontSize: '0.9rem'
            }}>
              No repository active
            </div>
          )}
        </div>
        <div className="content-area">
          {renderContent()}
        </div>
      </div>
    </div>
  );
}

export default App;
