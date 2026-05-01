const tabs = [
  { id: 'search', label: 'Search' },
  { id: 'topics', label: 'Topics' },
  { id: 'random', label: 'Random' }
]

function ProblemCard({ item, onSelect }) {
  return (
    <div className="result-card">
      <div className="result-title">
        <span>{item.name || item.title}</span>
        {item.code && <span className="result-code">{item.code}</span>}
      </div>
      <div className="result-meta">
        <span>Rating: {item.rating ?? 'N/A'}</span>
        <span>Tags: {item.tags?.length ? item.tags.join(', ') : 'N/A'}</span>
      </div>
      <div className="result-actions">
        <button type="button" className="primary" onClick={() => onSelect(item)}>
          Open & Load
        </button>
      </div>
    </div>
  )
}

export default function FetchModal({
  isOpen,
  onClose,
  activeTab,
  onChangeTab,
  searchQuery,
  setSearchQuery,
  searchResults,
  searchLoading,
  onSearch,
  topicsInput,
  setTopicsInput,
  topicsLimit,
  setTopicsLimit,
  topicsMinRating,
  setTopicsMinRating,
  topicsMaxRating,
  setTopicsMaxRating,
  topicsResults,
  topicsLoading,
  onTopicsSearch,
  randomTopicsInput,
  setRandomTopicsInput,
  randomMinRating,
  setRandomMinRating,
  randomMaxRating,
  setRandomMaxRating,
  randomResult,
  randomLoading,
  onRandom,
  onSelectProblem,
  problemUrl,
  setProblemUrl,
  onOpenProblem,
  onSync,
  onOpenLogin,
  syncLoading,
  fetchError,
  fetcherError,
  selectedProblem
}) {
  if (!isOpen) return null

  return (
    <div className="modal-overlay">
      <div className="panel shell modal">
        <div className="panel-header">
          <h3>Fetch Codeforces Problem</h3>
          <div className="panel-header-right">
            <button type="button" onClick={onOpenLogin}>
              Codeforces Login
            </button>
            <button type="button" onClick={onClose}>
              Close
            </button>
          </div>
        </div>

        <div className="modal-tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={activeTab === tab.id ? 'modal-tab active' : 'modal-tab'}
              onClick={() => onChangeTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="panel-body scrollable">
          {activeTab === 'search' && (
            <div className="section">
              <div className="section-body">
                <p className="muted">Search by exact name, code, or link</p>
                <div className="row">
                  <input
                    value={searchQuery}
                    onChange={(event) => setSearchQuery(event.target.value)}
                    placeholder="Two Buttons / 520B / https://codeforces.com/problemset/problem/520/B"
                  />
                  <button type="button" className="primary" onClick={onSearch} disabled={searchLoading}>
                    {searchLoading ? 'Searching...' : 'Search'}
                  </button>
                </div>
                {fetcherError && <p className="error-text">{fetcherError}</p>}
                <div className="result-list">
                  {searchResults.map((item) => (
                    <ProblemCard key={item.code || item.url} item={item} onSelect={onSelectProblem} />
                  ))}
                </div>
                {selectedProblem && (
                  <div className="section import-panel">
                    <div className="section-body">
                      <p className="muted">Selected: {selectedProblem.name || selectedProblem.title}</p>
                      <div className="row">
                        <input
                          value={problemUrl}
                          onChange={(event) => setProblemUrl(event.target.value)}
                          placeholder="https://codeforces.com/problemset/problem/4/A"
                        />
                        <button type="button" className="primary" onClick={onOpenProblem}>
                          Open Problem
                        </button>
                        <button type="button" onClick={onSync} disabled={syncLoading}>
                          {syncLoading ? 'Syncing...' : 'Sync Import'}
                        </button>
                      </div>
                      {fetchError && <p className="error-text">{fetchError}</p>}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'topics' && (
            <div className="section">
              <div className="section-body">
                <p className="muted">Fetch a list by topics</p>
                <div className="row">
                  <input
                    value={topicsInput}
                    onChange={(event) => setTopicsInput(event.target.value)}
                    placeholder="dp, graphs, greedy"
                  />
                </div>
                <div className="row">
                  <input
                    value={topicsLimit}
                    onChange={(event) => setTopicsLimit(event.target.value)}
                    placeholder="Limit"
                  />
                  <input
                    value={topicsMinRating}
                    onChange={(event) => setTopicsMinRating(event.target.value)}
                    placeholder="Min rating"
                  />
                  <input
                    value={topicsMaxRating}
                    onChange={(event) => setTopicsMaxRating(event.target.value)}
                    placeholder="Max rating"
                  />
                  <button type="button" className="primary" onClick={onTopicsSearch} disabled={topicsLoading}>
                    {topicsLoading ? 'Loading...' : 'Fetch'}
                  </button>
                </div>
                {fetcherError && <p className="error-text">{fetcherError}</p>}
                <div className="result-list">
                  {topicsResults.map((item) => (
                    <ProblemCard key={item.code || item.url} item={item} onSelect={onSelectProblem} />
                  ))}
                </div>
                {selectedProblem && (
                  <div className="section import-panel">
                    <div className="section-body">
                      <p className="muted">Selected: {selectedProblem.name || selectedProblem.title}</p>
                      <div className="row">
                        <input
                          value={problemUrl}
                          onChange={(event) => setProblemUrl(event.target.value)}
                          placeholder="https://codeforces.com/problemset/problem/4/A"
                        />
                        <button type="button" className="primary" onClick={onOpenProblem}>
                          Open Problem
                        </button>
                        <button type="button" onClick={onSync} disabled={syncLoading}>
                          {syncLoading ? 'Syncing...' : 'Sync Import'}
                        </button>
                      </div>
                      {fetchError && <p className="error-text">{fetchError}</p>}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'random' && (
            <div className="section">
              <div className="section-body">
                <p className="muted">Pick a random problem (user profile placeholder)</p>
                <div className="row">
                  <input
                    value={randomTopicsInput}
                    onChange={(event) => setRandomTopicsInput(event.target.value)}
                    placeholder="Topics (optional)"
                  />
                  <input
                    value={randomMinRating}
                    onChange={(event) => setRandomMinRating(event.target.value)}
                    placeholder="Min rating"
                  />
                  <input
                    value={randomMaxRating}
                    onChange={(event) => setRandomMaxRating(event.target.value)}
                    placeholder="Max rating"
                  />
                  <button type="button" className="primary" onClick={onRandom} disabled={randomLoading}>
                    {randomLoading ? 'Rolling...' : 'Random'}
                  </button>
                </div>
                {fetcherError && <p className="error-text">{fetcherError}</p>}
                <div className="result-list">
                  {randomResult && <ProblemCard item={randomResult} onSelect={onSelectProblem} />}
                </div>
                {selectedProblem && (
                  <div className="section import-panel">
                    <div className="section-body">
                      <p className="muted">Selected: {selectedProblem.name || selectedProblem.title}</p>
                      <div className="row">
                        <input
                          value={problemUrl}
                          onChange={(event) => setProblemUrl(event.target.value)}
                          placeholder="https://codeforces.com/problemset/problem/4/A"
                        />
                        <button type="button" className="primary" onClick={onOpenProblem}>
                          Open Problem
                        </button>
                        <button type="button" onClick={onSync} disabled={syncLoading}>
                          {syncLoading ? 'Syncing...' : 'Sync Import'}
                        </button>
                      </div>
                      {fetchError && <p className="error-text">{fetchError}</p>}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
