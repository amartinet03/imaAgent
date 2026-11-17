import { useState, useEffect } from 'react';
import { isAuthenticated, setAuthToken } from './api/client';
import { Sidebar } from './components/Sidebar';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { NewTender } from './pages/NewTender';
import { TenderDetail } from './pages/TenderDetail';
import { Settings } from './pages/Settings';
import { RadarPage } from './pages/RadarPage';
import { ToastProvider } from './components/Toast';

export function App() {
  const [authed, setAuthed] = useState<boolean>(false);
  const [currentView, setCurrentView] = useState<string>('dashboard');
  const [selectedTenderId, setSelectedTenderId] = useState<number | null>(null);

  useEffect(() => {
    // Check URL params for token support (matching Streamlit behavior)
    const params = new URLSearchParams(window.location.search);
    const tokenParam = params.get('token');
    if (tokenParam) {
      try {
        const user = atob(tokenParam);
        setAuthToken(tokenParam, user);
        setAuthed(true);
      } catch {
        // ignore
      }
    } else {
      setAuthed(isAuthenticated());
    }
  }, []);

  const handleOpenTender = (id: number) => {
    setSelectedTenderId(id);
    setCurrentView('detalle');
  };

  const handleNavigate = (view: string) => {
    if (view === 'login') {
      setAuthed(false);
      setCurrentView('dashboard');
      return;
    }
    setCurrentView(view);
  };

  if (!authed) {
    return (
      <ToastProvider>
        <Login onSuccess={() => setAuthed(true)} />
      </ToastProvider>
    );
  }

  return (
    <ToastProvider>
      <div className="flex h-screen w-screen overflow-hidden bg-slate-50 font-sans text-slate-800">
        <Sidebar currentView={currentView} onNavigate={handleNavigate} />
        <main className="flex-1 h-full overflow-y-auto bg-slate-50">
          <div className="p-8 max-w-7xl mx-auto">
            {currentView === 'dashboard' && (
              <Dashboard
                onSelectTender={handleOpenTender}
                onNavigate={handleNavigate}
              />
            )}
            {currentView === 'nueva_licitacion' && (
              <NewTender
                onBack={() => setCurrentView('dashboard')}
                onCreated={() => setCurrentView('dashboard')}
              />
            )}
            {currentView === 'detalle' && selectedTenderId && (
              <TenderDetail
                tenderId={selectedTenderId}
                onBack={() => setCurrentView('dashboard')}
              />
            )}
            {currentView === 'radar' && (
              <RadarPage
                onTenderCreated={(id) => handleOpenTender(id)}
              />
            )}
            {currentView === 'configuracion' && (
              <Settings onTenderCreated={() => setCurrentView('dashboard')} />
            )}
          </div>
        </main>
      </div>
    </ToastProvider>
  );
}

export default App;
