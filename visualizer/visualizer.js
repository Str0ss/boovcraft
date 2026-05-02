'use strict';

(() => {
  /* ============================================================== */
  /* visualizer entry point — feature 004 (tabs)                     */
  /* ============================================================== */

  /* ---------- page state ---------- */

  const pageState = {
    loadedFile: null,
    analysis: null,
    activeTab: 'summary',
    zoomState: null,
  };

  /* ---------- DOM refs ---------- */

  /** @type {HTMLElement|null} */ let appEl = null;
  /** @type {HTMLInputElement|null} */ let pickerEl = null;
  /** @type {HTMLElement|null} */ let reportEl = null;
  /** @type {HTMLElement|null} */ let errorEl = null;
  /** @type {HTMLElement|null} */ let tabStripEl = null;
  /** @type {HTMLElement|null} */ let loadedFileEl = null;

  /* ---------- constants ---------- */

  const REQUIRED_TOP_LEVEL_KEYS = [
    'match', 'settings', 'map', 'players',
    'observers', 'chat', 'diagnostics',
  ];

  const ERR_PARSE = "Couldn't parse this file as JSON.";
  const ERR_SHAPE = "This file doesn't look like a replay analysis.";
  const ERR_READ = "Couldn't read this file.";
  const ERR_NO_FILE = 'Please select a single .json file.';

  const RACE_NAMES = {
    H: 'Human',
    O: 'Orc',
    U: 'Undead',
    N: 'Night Elf',
    R: 'Random',
  };

  const PRODUCTION_CATEGORIES = [
    { key: 'buildings', label: 'Buildings', emptyState: 'No buildings recorded.' },
    { key: 'units', label: 'Units', emptyState: 'No units recorded.' },
    { key: 'upgrades', label: 'Upgrades', emptyState: 'No upgrades recorded.' },
    { key: 'items', label: 'Items', emptyState: 'No items recorded.' },
  ];

  const ACTION_TOTAL_LABELS = [
    ['buildtrain', 'Build / train'],
    ['ability', 'Ability'],
    ['item', 'Item'],
    ['rightclick', 'Right-click'],
    ['select', 'Select'],
    ['selecthotkey', 'Hotkey select'],
    ['assigngroup', 'Assign group'],
    ['subgroup', 'Subgroup'],
    ['basic', 'Basic'],
    ['removeunit', 'Remove unit'],
    ['esc', 'Esc'],
  ];

  const TABS = [
    { id: 'summary', label: 'Summary' },
    { id: 'timelines', label: 'Timelines' },
    { id: 'analysis', label: 'Analysis' },
    { id: 'map', label: 'Map' },
  ];

  const TIMELINE_CONFIG = {
    TARGET_BUCKET_PX: 10,
    MIN_BUCKET_MS: 250,
    MAX_BARS_HARD_CAP: 1000,
    NICE_INTERVALS_MS: [
      250, 500, 1000, 2000, 5000, 10000, 15000, 30000,
      60000, 120000, 300000, 600000, 900000, 1800000, 3600000,
    ],
    LAYOUT: {
      rowHeight: 90,
      rowPadding: 6,
      labelWidth: 160,
      axisRightPad: 16,
      axisHeight: 22,
      barAreaHeight: 56,
    },
    MAJOR_CATEGORIES: ['buildtrain', 'ability', 'item', 'removeunit', 'esc', 'transfer'],
    MINOR_CATEGORIES: ['rightclick', 'select', 'selecthotkey', 'basic', 'assigngroup', 'subgroup'],
    CATEGORY_COLOR: {
      buildtrain: '#3a86ff',
      ability: '#9d4edd',
      item: '#ffb703',
      removeunit: '#fb5607',
      esc: '#8d99ae',
      transfer: '#06d6a0',
      rightclick: '#cad2c5',
      select: '#a8b5a0',
      selecthotkey: '#84a98c',
      basic: '#bdb2a7',
      assigngroup: '#dda15e',
      subgroup: '#bdb2a7',
    },
    CATEGORY_LABEL: {
      buildtrain: 'Build / train',
      ability: 'Ability',
      item: 'Item',
      removeunit: 'Remove unit',
      esc: 'Esc',
      transfer: 'Transfer',
      rightclick: 'Right-click',
      select: 'Select',
      selecthotkey: 'Hotkey select',
      basic: 'Basic',
      assigngroup: 'Assign group',
      subgroup: 'Subgroup',
    },
  };

  /* ---------- utilities ---------- */

  function formatTimeMs(ms, totalMs) {
    const safeMs = Math.max(0, Math.floor(Number(ms) || 0));
    const totalSeconds = Math.floor(safeMs / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    if (totalMs < 3_600_000) {
      return `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }
    const hours = Math.floor(minutes / 60);
    const remMinutes = minutes % 60;
    return `${hours}:${remMinutes.toString().padStart(2, '0')}:${seconds
      .toString()
      .padStart(2, '0')}`;
  }

  function formatInt(n) {
    return Number(n).toLocaleString('en-US');
  }

  function validateAnalysisShape(parsed) {
    if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return { ok: false, message: ERR_SHAPE };
    }
    for (const key of REQUIRED_TOP_LEVEL_KEYS) {
      if (!(key in parsed)) return { ok: false, message: ERR_SHAPE };
    }
    if (
      parsed.match === null ||
      typeof parsed.match !== 'object' ||
      Array.isArray(parsed.match)
    ) {
      return { ok: false, message: ERR_SHAPE };
    }
    if (!Array.isArray(parsed.players)) return { ok: false, message: ERR_SHAPE };
    if (!Array.isArray(parsed.observers)) return { ok: false, message: ERR_SHAPE };
    if (!Array.isArray(parsed.chat)) return { ok: false, message: ERR_SHAPE };
    return { ok: true };
  }

  function el(tag, opts = {}, children = []) {
    const node = document.createElement(tag);
    if (opts.class) node.className = opts.class;
    if (opts.text != null) node.textContent = opts.text;
    if (opts.title) node.title = opts.title;
    if (opts.attrs) {
      for (const [k, v] of Object.entries(opts.attrs)) node.setAttribute(k, v);
    }
    if (opts.style) {
      for (const [k, v] of Object.entries(opts.style)) node.style[k] = v;
    }
    for (const child of children) {
      if (child == null) continue;
      node.appendChild(typeof child === 'string' ? document.createTextNode(child) : child);
    }
    return node;
  }

  const SVG_NS = 'http://www.w3.org/2000/svg';

  function svgEl(tag, attrs = {}, children = []) {
    const node = document.createElementNS(SVG_NS, tag);
    for (const [k, v] of Object.entries(attrs)) {
      node.setAttribute(k, String(v));
    }
    for (const c of children) {
      if (c == null) continue;
      node.appendChild(c);
    }
    return node;
  }

  function entityLabelEl(entity, kind = 'span') {
    const node = document.createElement(kind);
    node.classList.add('entity');
    node.textContent = entity.name;
    if (entity.unknown === true) {
      node.classList.add('entity--unknown');
      node.title = `Unknown entity id: ${entity.id}`;
      const badge = document.createElement('span');
      badge.classList.add('unknown-badge');
      badge.textContent = '[?]';
      node.appendChild(badge);
    }
    return node;
  }

  function raceLabel(player) {
    const chosen = RACE_NAMES[player.race] || player.race;
    if (player.race === 'R' && player.raceDetected && player.raceDetected !== 'R') {
      const detected = RACE_NAMES[player.raceDetected] || player.raceDetected;
      return `Random → ${detected}`;
    }
    return chosen;
  }

  /* ---------- file load + render lifecycle ---------- */

  function showError(message) {
    if (!errorEl) return;
    errorEl.textContent = message;
    errorEl.hidden = false;
    clearReport();
  }

  function clearError() {
    if (!errorEl) return;
    errorEl.textContent = '';
    errorEl.hidden = true;
  }

  function clearReport() {
    if (!reportEl) return;
    reportEl.replaceChildren();
    reportEl.hidden = true;
    if (tabStripEl) tabStripEl.hidden = true;
    if (loadedFileEl) {
      loadedFileEl.textContent = '';
      loadedFileEl.hidden = true;
    }
    pageState.analysis = null;
    pageState.loadedFile = null;
    pageState.activeTab = 'summary';
    pageState.zoomState = null;
  }

  function loadFile(file) {
    if (!file) {
      showError(ERR_NO_FILE);
      return;
    }
    const reader = new FileReader();
    reader.onerror = () => showError(ERR_READ);
    reader.onload = () => {
      const text = String(reader.result ?? '');
      let parsed;
      try {
        parsed = JSON.parse(text);
      } catch (_e) {
        showError(ERR_PARSE);
        return;
      }
      const check = validateAnalysisShape(parsed);
      if (!check.ok) {
        showError(check.message);
        return;
      }
      clearError();
      pageState.analysis = parsed;
      pageState.loadedFile = { name: file.name, loadedAt: Date.now() };
      pageState.activeTab = 'summary';
      pageState.zoomState = { visibleStartMs: 0, visibleEndMs: parsed.match.durationMs };
      if (loadedFileEl) {
        loadedFileEl.textContent = file.name;
        loadedFileEl.hidden = false;
      }
      renderTabStrip();
      if (tabStripEl) tabStripEl.hidden = false;
      reportEl.hidden = false;
      renderActiveTab();
    };
    reader.readAsText(file);
  }

  /* ---------- tab routing ---------- */

  function renderTabStrip() {
    if (!tabStripEl) return;
    tabStripEl.replaceChildren();
    for (const tab of TABS) {
      const btn = el('button', {
        class: 'tab' + (tab.id === pageState.activeTab ? ' tab--active' : ''),
        text: tab.label,
        attrs: {
          type: 'button',
          role: 'tab',
          'aria-selected': tab.id === pageState.activeTab ? 'true' : 'false',
          'data-tab': tab.id,
        },
      });
      btn.addEventListener('click', () => setActiveTab(tab.id));
      tabStripEl.appendChild(btn);
    }
  }

  function setActiveTab(name) {
    if (!pageState.analysis) return;
    if (!TABS.some(t => t.id === name)) return;
    pageState.activeTab = name;
    if (tabStripEl) {
      for (const btn of tabStripEl.querySelectorAll('.tab')) {
        const isActive = btn.dataset.tab === name;
        btn.classList.toggle('tab--active', isActive);
        btn.setAttribute('aria-selected', isActive ? 'true' : 'false');
      }
    }
    renderActiveTab();
  }

  function renderActiveTab() {
    if (!pageState.analysis || !reportEl) return;
    let body;
    switch (pageState.activeTab) {
      case 'summary':   body = renderSummaryTab(); break;
      case 'timelines': body = renderTimelinesTab(); break;
      case 'analysis':  body = renderAnalysisStub(); break;
      case 'map':       body = renderMapStub(); break;
      default:          body = renderSummaryTab();
    }
    reportEl.replaceChildren(body);
  }

  /* ============================================================== */
  /* Summary tab                                                     */
  /* ============================================================== */

  function renderSummaryTab() {
    const analysis = pageState.analysis;
    const durationMs = analysis.match.durationMs;
    const tab = el('section', { class: 'tab-content tab-content--summary' });
    tab.appendChild(renderMatchHeader(analysis, durationMs));
    tab.appendChild(renderTeams(analysis));
    tab.appendChild(renderChat(analysis.chat, durationMs));
    tab.appendChild(renderObservers(analysis.observers));
    return tab;
  }

  function renderMatchHeader(analysis, durationMs) {
    const m = analysis.match;
    const settings = analysis.settings || {};
    const winnerLabel = m.winner === null ? 'Undetermined' : `Team ${m.winner.teamId}`;
    const winnerCls = m.winner === null ? 'outcome outcome--undetermined' : 'outcome outcome--winner';

    const map = analysis.map || {};
    const mapName = map.file || map.path || '(unknown map)';

    return el('section', { class: 'match-header' }, [
      el('div', { class: 'match-header-line' }, [
        el('span', { class: winnerCls, text: `Outcome: ${winnerLabel}` }),
        el('span', { class: 'sep', text: '·' }),
        el('span', { class: 'duration', text: `Duration ${formatTimeMs(durationMs, durationMs)}` }),
        el('span', { class: 'sep', text: '·' }),
        el('span', { class: 'gametype', text: `${m.gameType} — ${m.matchup}` }),
        el('span', { class: 'sep', text: '·' }),
        el('span', { class: 'mapname', text: mapName, title: map.path || mapName }),
        el('span', { class: 'sep', text: '·' }),
        el('span', { class: 'version', text: `v${m.version} (build ${m.buildNumber})` }),
      ]),
      el('dl', { class: 'lobby-settings' }, [
        ...kvPair('Game', m.gameName),
        ...kvPair('Creator', m.creator),
        ...kvPair('Speed', settings.speed),
        ...kvPair('Observer mode', settings.observerMode),
        ...kvPair('Fixed teams', settings.fixedTeams ? 'yes' : 'no'),
        ...kvPair('Teams together', settings.teamsTogether ? 'yes' : 'no'),
        ...kvPair('Random races', settings.randomRaces ? 'yes' : 'no'),
        ...kvPair('Random heroes', settings.randomHero ? 'yes' : 'no'),
      ]),
    ]);
  }

  function kvPair(label, value) {
    if (value == null || value === '') return [];
    return [
      el('dt', { text: label }),
      el('dd', { text: String(value) }),
    ];
  }

  function groupPlayersByTeam(players) {
    const map = new Map();
    for (const p of players) {
      const arr = map.get(p.teamId) || [];
      arr.push(p);
      map.set(p.teamId, arr);
    }
    return new Map([...map.entries()].sort((a, b) => a[0] - b[0]));
  }

  function renderTeams(analysis) {
    const grouping = groupPlayersByTeam(analysis.players);
    const wrapper = el('section', { class: 'teams' });
    for (const [teamId, players] of grouping.entries()) {
      const isWinningTeam = players.length > 0 && players.every(p => p.isWinner);
      const teamHeaderText = isWinningTeam ? `Team ${teamId} — winners` : `Team ${teamId}`;
      const teamSection = el('section', { class: 'team' }, [
        el('h2', {
          class: isWinningTeam ? 'team-header team-header--winner' : 'team-header',
          text: teamHeaderText,
        }),
      ]);
      const grid = el('div', { class: 'team-grid' });
      for (const p of players) {
        grid.appendChild(renderPlayerPanelSummary(p, analysis));
      }
      teamSection.appendChild(grid);
      wrapper.appendChild(teamSection);
    }
    return wrapper;
  }

  function renderPlayerPanelSummary(player, analysis) {
    const panel = el('article', {
      class: 'player-panel',
      style: { borderLeftColor: player.color || '#888' },
    });
    const headerChildren = [
      el('span', { class: 'player-name', text: player.name }),
      el('span', { class: 'player-race', text: raceLabel(player) }),
      el('span', { class: 'player-apm', text: `${player.apm} APM` }),
    ];
    if (player.isWinner) {
      headerChildren.push(el('span', { class: 'badge--winner', text: 'Winner' }));
    }
    panel.appendChild(el('header', { class: 'player-panel-header' }, headerChildren));
    panel.appendChild(el('div', { class: 'player-meta' }, [
      el('span', {
        class: 'color-swatch',
        title: player.color,
        style: { backgroundColor: player.color || '#888' },
      }),
      el('span', { class: 'slot-id', text: `Slot ${player.id}` }),
      el('span', { class: 'team-id', text: `Team ${player.teamId}` }),
    ]));
    panel.appendChild(renderActionTotals(player));
    panel.appendChild(renderGroupHotkeys(player));
    panel.appendChild(renderProductionAggregation(player));
    panel.appendChild(renderHeroAggregation(player));
    panel.appendChild(renderTransferAggregation(player, analysis));
    return panel;
  }

  function renderActionTotals(player) {
    const totals = (player.actions && player.actions.totals) || {};
    const dl = el('dl', { class: 'action-totals' });
    for (const [key, label] of ACTION_TOTAL_LABELS) {
      const v = totals[key];
      if (v == null) continue;
      dl.appendChild(el('dt', { text: label }));
      dl.appendChild(el('dd', { text: formatInt(v) }));
    }
    return el('section', { class: 'panel-section' }, [
      el('h3', { class: 'panel-section-title', text: 'Action totals' }),
      dl,
    ]);
  }

  function renderGroupHotkeys(player) {
    const hk = player.groupHotkeys || {};
    const table = el('table', { class: 'hotkey-table' });
    table.appendChild(el('thead', {}, [
      el('tr', {}, [
        el('th', { text: 'Key' }),
        el('th', { text: 'Assigned' }),
        el('th', { text: 'Used' }),
      ]),
    ]));
    const tbody = el('tbody');
    for (let k = 0; k <= 9; k++) {
      const cell = hk[String(k)] || hk[k] || { assigned: 0, used: 0 };
      tbody.appendChild(el('tr', {}, [
        el('td', { text: String(k) }),
        el('td', { text: formatInt(cell.assigned || 0) }),
        el('td', { text: formatInt(cell.used || 0) }),
      ]));
    }
    table.appendChild(tbody);
    return el('section', { class: 'panel-section' }, [
      el('h3', { class: 'panel-section-title', text: 'Group hotkeys' }),
      table,
    ]);
  }

  /* ---------- aggregations ---------- */

  function aggregateProduction(player) {
    const out = {};
    for (const cat of PRODUCTION_CATEGORIES) {
      const sub = (player.production && player.production[cat.key]) || { summary: {} };
      const rows = Object.values(sub.summary || {}).map(entry => ({
        id: entry.id,
        name: entry.name,
        unknown: entry.unknown === true,
        count: entry.count || 0,
      }));
      rows.sort((a, b) => a.name.localeCompare(b.name));
      out[cat.key] = rows;
    }
    return out;
  }

  function aggregateHeroes(player) {
    const heroes = player.heroes || [];
    return heroes.map(hero => ({
      id: hero.id,
      name: hero.name,
      unknown: hero.unknown === true,
      finalLevel: hero.level || 0,
      abilityChain: (hero.abilityOrder || []).map(ab => ({
        id: ab.id,
        name: ab.name,
        unknown: ab.unknown === true,
        level: ab.level,
      })),
    }));
  }

  function aggregateTransfers(player, analysis) {
    const recipients = new Map();
    for (const t of player.resourceTransfers || []) {
      const recipientName = t.toPlayerName || playerNameFromId(t.toPlayerId, analysis) || `Player ${t.toPlayerId}`;
      for (const resource of ['gold', 'lumber']) {
        const amount = t[resource] || 0;
        if (amount <= 0) continue;
        const key = `${t.toPlayerId}|${resource}`;
        const cur = recipients.get(key) || {
          recipientName,
          resource,
          total: 0,
          count: 0,
        };
        cur.total += amount;
        cur.count += 1;
        recipients.set(key, cur);
      }
    }
    return [...recipients.values()].sort((a, b) => b.total - a.total);
  }

  function playerNameFromId(playerId, analysis) {
    if (!analysis) return null;
    const found = (analysis.players || []).find(p => p.id === playerId);
    return found ? found.name : null;
  }

  function renderProductionAggregation(player) {
    const wrapper = el('section', { class: 'panel-section production' }, [
      el('h3', { class: 'panel-section-title', text: 'Production' }),
    ]);
    const agg = aggregateProduction(player);
    for (const cat of PRODUCTION_CATEGORIES) {
      const rows = agg[cat.key];
      const total = rows.reduce((s, r) => s + r.count, 0);
      const subSection = el('section', { class: `prod-cat prod-cat--${cat.key}` }, [
        el('h4', { class: 'prod-cat-title', text: `${cat.label} (${total})` }),
      ]);
      if (rows.length === 0) {
        subSection.appendChild(el('p', { class: 'empty-state', text: cat.emptyState }));
      } else {
        const ul = el('ul', { class: 'prod-agg-list' });
        for (const r of rows) {
          ul.appendChild(el('li', {}, [
            entityLabelEl(r),
            el('span', { class: 'count', text: ` (×${r.count})` }),
          ]));
        }
        subSection.appendChild(ul);
      }
      wrapper.appendChild(subSection);
    }
    return wrapper;
  }

  function renderHeroAggregation(player) {
    const wrapper = el('section', { class: 'panel-section heroes' }, [
      el('h3', { class: 'panel-section-title', text: 'Heroes' }),
    ]);
    const heroes = aggregateHeroes(player);
    if (heroes.length === 0) {
      wrapper.appendChild(el('p', { class: 'empty-state', text: 'No heroes used.' }));
      return wrapper;
    }
    const ul = el('ul', { class: 'hero-agg-list' });
    for (const hero of heroes) {
      const heroName = entityLabelEl(hero, 'span');
      const li = el('li', { class: 'hero-agg' }, [
        heroName,
        el('span', { class: 'hero-level', text: ` — Level ${hero.finalLevel}` }),
      ]);
      if (hero.abilityChain.length === 0) {
        li.appendChild(el('span', { class: 'empty-inline', text: ' (no abilities learned)' }));
      } else {
        li.appendChild(document.createTextNode(': '));
        const chain = el('span', { class: 'ability-chain' });
        hero.abilityChain.forEach((ab, idx) => {
          if (idx > 0) {
            chain.appendChild(el('span', { class: 'arrow', text: ' → ' }));
          }
          const seg = el('span', { class: 'ability-seg' }, [
            entityLabelEl(ab, 'span'),
            el('span', { class: 'ability-level', text: ` (L${ab.level})` }),
          ]);
          chain.appendChild(seg);
        });
        li.appendChild(chain);
      }
      ul.appendChild(li);
    }
    wrapper.appendChild(ul);
    return wrapper;
  }

  function renderTransferAggregation(player, analysis) {
    const wrapper = el('section', { class: 'panel-section transfers' }, [
      el('h3', { class: 'panel-section-title', text: 'Resource transfers' }),
    ]);
    const rows = aggregateTransfers(player, analysis);
    if (rows.length === 0) {
      wrapper.appendChild(el('p', { class: 'empty-state', text: 'No allied resource transfers.' }));
      return wrapper;
    }
    const ul = el('ul', { class: 'transfer-agg-list' });
    for (const r of rows) {
      ul.appendChild(el('li', {}, [
        el('span', { class: 'recipient', text: r.recipientName }),
        ': ',
        el('span', { class: 'amount', text: `${formatInt(r.total)} ${r.resource}` }),
        el('span', { class: 'count', text: ` (${r.count} transfer${r.count === 1 ? '' : 's'})` }),
      ]));
    }
    wrapper.appendChild(ul);
    return wrapper;
  }

  /* ---------- chat & observers ---------- */

  function renderChat(chat, durationMs) {
    const wrapper = el('section', { class: 'chat-section' }, [
      el('h2', { class: 'section-header', text: `Chat (${chat ? chat.length : 0})` }),
    ]);
    if (!chat || chat.length === 0) {
      wrapper.appendChild(el('p', { class: 'empty-state', text: 'No in-game chat in this replay.' }));
      return wrapper;
    }
    const ol = el('ol', { class: 'chat-list' });
    for (const msg of chat) {
      const channelCls = `channel channel--${(msg.mode || 'all').toLowerCase()}`;
      const li = el('li', { class: 'chat-row' }, [
        el('span', { class: 'time', text: formatTimeMs(msg.timeMs, durationMs) }),
        el('span', { class: channelCls, text: msg.mode || 'All' }),
        el('span', { class: 'chat-sender', text: msg.playerName || `(player ${msg.playerId})` }),
        el('span', { class: 'chat-text', text: msg.text || '' }),
      ]);
      ol.appendChild(li);
    }
    wrapper.appendChild(ol);
    return wrapper;
  }

  function renderObservers(observers) {
    const wrapper = el('section', { class: 'observers-section' }, [
      el('h2', { class: 'section-header', text: `Observers (${observers ? observers.length : 0})` }),
    ]);
    if (!observers || observers.length === 0) {
      wrapper.appendChild(el('p', { class: 'empty-state', text: 'No observers.' }));
      return wrapper;
    }
    wrapper.appendChild(el('p', { class: 'observer-list', text: observers.join(', ') }));
    return wrapper;
  }

  /* ============================================================== */
  /* Timelines tab                                                   */
  /* ============================================================== */

  function collectPlayerEvents(player) {
    const events = [];
    for (const ev of (player.actions && player.actions.timedActions) || []) {
      events.push({ timeMs: ev.timeMs, category: ev.category });
    }
    for (const t of player.resourceTransfers || []) {
      events.push({ timeMs: t.timeMs, category: 'transfer' });
    }
    events.sort((a, b) => a.timeMs - b.timeMs);
    return events;
  }

  function chooseBucketWidth(visibleMs, viewportPx) {
    const target = Math.max(8, Math.floor(viewportPx / TIMELINE_CONFIG.TARGET_BUCKET_PX));
    const ideal = Math.max(1, visibleMs / target);
    const intervals = TIMELINE_CONFIG.NICE_INTERVALS_MS;
    let chosen = intervals[intervals.length - 1];
    for (const v of intervals) {
      if (v >= ideal) { chosen = v; break; }
    }
    if (chosen < TIMELINE_CONFIG.MIN_BUCKET_MS) chosen = TIMELINE_CONFIG.MIN_BUCKET_MS;
    const bars = Math.ceil(visibleMs / chosen);
    if (bars > TIMELINE_CONFIG.MAX_BARS_HARD_CAP) {
      const minWidth = visibleMs / TIMELINE_CONFIG.MAX_BARS_HARD_CAP;
      for (const v of intervals) {
        if (v >= minWidth) { return v; }
      }
      return intervals[intervals.length - 1];
    }
    return chosen;
  }

  function bucketEvents(events, startMs, endMs, bucketWidthMs) {
    if (bucketWidthMs <= 0) return [];
    const bucketCount = Math.max(1, Math.ceil((endMs - startMs) / bucketWidthMs));
    const buckets = [];
    for (let i = 0; i < bucketCount; i++) {
      buckets.push({
        start: startMs + i * bucketWidthMs,
        end: Math.min(endMs, startMs + (i + 1) * bucketWidthMs),
        counts: {},
        total: 0,
      });
    }
    for (const ev of events) {
      if (ev.timeMs < startMs || ev.timeMs >= endMs) continue;
      const idx = Math.min(bucketCount - 1, Math.floor((ev.timeMs - startMs) / bucketWidthMs));
      const b = buckets[idx];
      b.counts[ev.category] = (b.counts[ev.category] || 0) + 1;
      b.total += 1;
    }
    return buckets;
  }

  function clampZoom(zoomState, durationMs) {
    let { visibleStartMs, visibleEndMs } = zoomState;
    visibleStartMs = Math.max(0, Math.min(visibleStartMs, durationMs - 1));
    visibleEndMs = Math.max(visibleStartMs + TIMELINE_CONFIG.MIN_BUCKET_MS, Math.min(visibleEndMs, durationMs));
    return { visibleStartMs, visibleEndMs };
  }

  function getViewportPx() {
    if (!reportEl) return 1024;
    const rect = reportEl.getBoundingClientRect();
    return Math.max(640, rect.width - TIMELINE_CONFIG.LAYOUT.labelWidth - TIMELINE_CONFIG.LAYOUT.axisRightPad - 32);
  }

  function renderTimelinesTab() {
    const analysis = pageState.analysis;
    const durationMs = analysis.match.durationMs;
    pageState.zoomState = clampZoom(pageState.zoomState || { visibleStartMs: 0, visibleEndMs: durationMs }, durationMs);
    const { visibleStartMs, visibleEndMs } = pageState.zoomState;
    const viewportPx = getViewportPx();
    const bucketWidthMs = chooseBucketWidth(visibleEndMs - visibleStartMs, viewportPx);

    const tab = el('section', { class: 'tab-content tab-content--timelines' });
    tab.appendChild(renderTimelineControls(durationMs, bucketWidthMs));
    tab.appendChild(renderTimelineLegend());

    const stack = el('div', { class: 'timeline-stack' });
    for (const player of analysis.players) {
      stack.appendChild(renderPlayerHistogramRow(player, viewportPx, bucketWidthMs));
    }
    tab.appendChild(stack);
    return tab;
  }

  function renderTimelineControls(durationMs, bucketWidthMs) {
    const { visibleStartMs, visibleEndMs } = pageState.zoomState;
    const visibleMs = visibleEndMs - visibleStartMs;

    const wrapper = el('section', { class: 'timeline-controls' });

    const zoomRow = el('div', { class: 'tl-control-row' });
    zoomRow.appendChild(el('label', { text: 'Zoom', attrs: { for: 'tl-zoom' } }));

    const minVisible = Math.max(TIMELINE_CONFIG.MIN_BUCKET_MS, durationMs / 1000);
    const maxLog = Math.log(durationMs / minVisible);
    const curLog = Math.log(durationMs / visibleMs);
    const slider = el('input', {
      attrs: {
        id: 'tl-zoom',
        type: 'range',
        min: '0',
        max: '1000',
        step: '1',
        value: String(Math.round((curLog / maxLog) * 1000)),
      },
    });
    slider.addEventListener('input', () => {
      const ratio = Number(slider.value) / 1000;
      const newVisible = durationMs * Math.exp(-maxLog * ratio);
      const center = (pageState.zoomState.visibleStartMs + pageState.zoomState.visibleEndMs) / 2;
      let newStart = Math.max(0, center - newVisible / 2);
      let newEnd = Math.min(durationMs, newStart + newVisible);
      newStart = Math.max(0, newEnd - newVisible);
      pageState.zoomState = { visibleStartMs: newStart, visibleEndMs: newEnd };
      renderActiveTab();
    });
    zoomRow.appendChild(slider);
    zoomRow.appendChild(el('span', { class: 'tl-zoom-readout', text: `bucket ${formatTimeMs(bucketWidthMs, durationMs)}` }));
    wrapper.appendChild(zoomRow);

    const panRow = el('div', { class: 'tl-control-row' });
    panRow.appendChild(el('label', { text: 'Pan' }));
    const mkBtn = (label, fn) => {
      const b = el('button', { class: 'tl-btn', text: label, attrs: { type: 'button' } });
      b.addEventListener('click', fn);
      return b;
    };
    panRow.appendChild(mkBtn('⏮', () => panTo(0)));
    panRow.appendChild(mkBtn('◀', () => panBy(-visibleMs * 0.5)));
    panRow.appendChild(mkBtn('▶', () => panBy(visibleMs * 0.5)));
    panRow.appendChild(mkBtn('⏭', () => panTo(durationMs - visibleMs)));
    panRow.appendChild(mkBtn('Reset zoom', () => {
      pageState.zoomState = { visibleStartMs: 0, visibleEndMs: durationMs };
      renderActiveTab();
    }));
    panRow.appendChild(el('span', { class: 'tl-readout', text:
      `view: ${formatTimeMs(visibleStartMs, durationMs)} – ${formatTimeMs(visibleEndMs, durationMs)}` }));
    wrapper.appendChild(panRow);
    return wrapper;
  }

  function panBy(deltaMs) {
    const durationMs = pageState.analysis.match.durationMs;
    let { visibleStartMs, visibleEndMs } = pageState.zoomState;
    const w = visibleEndMs - visibleStartMs;
    visibleStartMs = Math.max(0, Math.min(durationMs - w, visibleStartMs + deltaMs));
    visibleEndMs = visibleStartMs + w;
    pageState.zoomState = { visibleStartMs, visibleEndMs };
    renderActiveTab();
  }

  function panTo(startMs) {
    const durationMs = pageState.analysis.match.durationMs;
    const w = pageState.zoomState.visibleEndMs - pageState.zoomState.visibleStartMs;
    const newStart = Math.max(0, Math.min(durationMs - w, startMs));
    pageState.zoomState = { visibleStartMs: newStart, visibleEndMs: newStart + w };
    renderActiveTab();
  }

  function renderTimelineLegend() {
    const wrapper = el('section', { class: 'timeline-legend' }, [
      el('span', { class: 'legend-group-title', text: 'Major: ' }),
    ]);
    for (const c of TIMELINE_CONFIG.MAJOR_CATEGORIES) {
      wrapper.appendChild(legendChip(c, true));
    }
    wrapper.appendChild(el('span', { class: 'legend-group-title legend-minor', text: '   Minor: ' }));
    for (const c of TIMELINE_CONFIG.MINOR_CATEGORIES) {
      wrapper.appendChild(legendChip(c, false));
    }
    return wrapper;
  }

  function legendChip(category, isMajor) {
    return el('span', { class: `legend-chip ${isMajor ? 'legend-chip--major' : 'legend-chip--minor'}` }, [
      el('span', { class: 'legend-swatch', style: { backgroundColor: TIMELINE_CONFIG.CATEGORY_COLOR[category] || '#888' } }),
      el('span', { class: 'legend-label', text: TIMELINE_CONFIG.CATEGORY_LABEL[category] || category }),
    ]);
  }

  function renderPlayerHistogramRow(player, viewportPx, bucketWidthMs) {
    const analysis = pageState.analysis;
    const durationMs = analysis.match.durationMs;
    const { visibleStartMs, visibleEndMs } = pageState.zoomState;
    const events = collectPlayerEvents(player);
    const buckets = bucketEvents(events, visibleStartMs, visibleEndMs, bucketWidthMs);

    const row = el('article', {
      class: 'tl-row',
      style: { borderLeftColor: player.color || '#888' },
    });

    const labelCol = el('div', { class: 'tl-row-label-col' }, [
      el('span', {
        class: 'color-swatch',
        style: { backgroundColor: player.color || '#888' },
        title: player.color,
      }),
      el('div', { class: 'tl-row-name-block' }, [
        el('span', { class: 'tl-row-name', text: player.name }),
        el('span', { class: 'tl-row-meta', text: `${raceLabel(player)} · ${player.apm} APM${player.isWinner ? ' · Winner' : ''}` }),
      ]),
    ]);
    row.appendChild(labelCol);

    const layout = TIMELINE_CONFIG.LAYOUT;
    const svgWidth = viewportPx;
    const svgHeight = layout.barAreaHeight + layout.axisHeight;
    const svg = svgEl('svg', {
      class: 'tl-svg',
      width: svgWidth,
      height: svgHeight,
      viewBox: `0 0 ${svgWidth} ${svgHeight}`,
      preserveAspectRatio: 'none',
      role: 'img',
      'aria-label': `Timeline for ${player.name}`,
    });

    const visibleMs = visibleEndMs - visibleStartMs || 1;
    const xOf = (timeMs) => ((timeMs - visibleStartMs) / visibleMs) * svgWidth;

    let maxTotal = 0;
    for (const b of buckets) if (b.total > maxTotal) maxTotal = b.total;
    if (maxTotal === 0) maxTotal = 1;

    const barAreaTop = 0;
    const barAreaBottom = layout.barAreaHeight;

    for (const b of buckets) {
      if (b.total === 0) continue;
      const x0 = xOf(b.start);
      const x1 = xOf(b.end);
      const w = Math.max(1, x1 - x0 - 1);

      let yCursor = barAreaBottom;
      const orderedCats = [...TIMELINE_CONFIG.MINOR_CATEGORIES, ...TIMELINE_CONFIG.MAJOR_CATEGORIES];
      for (const cat of orderedCats) {
        const n = b.counts[cat] || 0;
        if (n === 0) continue;
        const segH = (n / maxTotal) * (barAreaBottom - barAreaTop);
        const segY = yCursor - segH;
        const isMajor = TIMELINE_CONFIG.MAJOR_CATEGORIES.includes(cat);
        svg.appendChild(svgEl('rect', {
          x: x0,
          y: segY,
          width: w,
          height: Math.max(0.5, segH),
          fill: TIMELINE_CONFIG.CATEGORY_COLOR[cat] || '#888',
          opacity: isMajor ? '1' : '0.55',
          class: `tl-bar tl-bar--${cat} ${isMajor ? 'tl-bar--major' : 'tl-bar--minor'}`,
        }));
        yCursor = segY;
      }
      const hit = svgEl('rect', {
        x: x0,
        y: 0,
        width: x1 - x0,
        height: barAreaBottom,
        fill: 'transparent',
        tabindex: '0',
        class: 'tl-bar-hit',
      });
      const title = svgEl('title', {});
      title.appendChild(document.createTextNode(bucketTooltipText(b, durationMs)));
      hit.appendChild(title);
      svg.appendChild(hit);
    }

    const axisY = barAreaBottom + 1;
    svg.appendChild(svgEl('line', {
      x1: 0, y1: axisY, x2: svgWidth, y2: axisY,
      class: 'tl-axis-line',
    }));
    const ticks = computeAxisTicks(visibleStartMs, visibleEndMs, bucketWidthMs);
    for (const t of ticks) {
      const x = xOf(t);
      svg.appendChild(svgEl('line', {
        x1: x, y1: axisY, x2: x, y2: axisY + 4,
        class: 'tl-tick',
      }));
      svg.appendChild(svgEl('text', {
        x, y: axisY + 16,
        'text-anchor': 'middle',
        class: 'tl-tick-label',
      }, [document.createTextNode(formatTimeMs(t, durationMs))]));
    }

    row.appendChild(svg);
    return row;
  }

  function bucketTooltipText(bucket, durationMs) {
    const lines = [];
    lines.push(`${formatTimeMs(bucket.start, durationMs)} – ${formatTimeMs(bucket.end, durationMs)}`);
    lines.push(`Total: ${bucket.total}`);
    const cats = Object.entries(bucket.counts)
      .filter(([, n]) => n > 0)
      .sort((a, b) => b[1] - a[1]);
    for (const [cat, n] of cats) {
      lines.push(`  ${TIMELINE_CONFIG.CATEGORY_LABEL[cat] || cat}: ${n}`);
    }
    return lines.join('\n');
  }

  function computeAxisTicks(startMs, endMs, bucketWidthMs) {
    const visibleMs = endMs - startMs;
    const desiredTicks = 6;
    const idealStep = visibleMs / desiredTicks;
    const intervals = TIMELINE_CONFIG.NICE_INTERVALS_MS;
    let step = intervals[intervals.length - 1];
    for (const v of intervals) {
      if (v >= idealStep) { step = v; break; }
    }
    if (step < bucketWidthMs) step = bucketWidthMs;
    const ticks = [];
    const first = Math.ceil(startMs / step) * step;
    for (let t = first; t <= endMs; t += step) {
      ticks.push(t);
    }
    if (ticks.length === 0 || ticks[0] !== startMs) ticks.unshift(startMs);
    return ticks;
  }

  /* ============================================================== */
  /* Stub tabs                                                       */
  /* ============================================================== */

  function renderAnalysisStub() {
    return el('section', { class: 'tab-content tab-content--stub' }, [
      el('h2', { class: 'stub-heading', text: 'Analysis (coming soon)' }),
      el('p', { class: 'stub-body', text:
        'This tab will host an LLM-ready textual analysis of the loaded replay — a separate analysis pipeline that has not yet been implemented.' }),
      el('p', { class: 'stub-body', text:
        'Switch back to the Summary or Timelines tab for the data the visualizer currently surfaces.' }),
    ]);
  }

  function renderMapStub() {
    const map = (pageState.analysis && pageState.analysis.map) || {};
    const mapName = map.file || map.path || '(unknown map)';
    return el('section', { class: 'tab-content tab-content--stub' }, [
      el('h2', { class: 'stub-heading', text: 'Map (coming soon)' }),
      el('p', { class: 'stub-body', text:
        'This tab will visualize per-player actions on the match map — also not yet implemented.' }),
      el('p', { class: 'stub-body', text: `Map for this match: ${mapName}` }),
    ]);
  }

  /* ============================================================== */
  /* Drag-and-drop (carried from feature 003)                        */
  /* ============================================================== */

  function bindDragAndDrop() {
    const dropzoneEl = document.getElementById('dropzone');
    if (!dropzoneEl) return;

    let dragDepth = 0;
    const showDropzone = () => { dropzoneEl.hidden = false; };
    const hideDropzone = () => { dropzoneEl.hidden = true; dragDepth = 0; };

    document.addEventListener('dragenter', (e) => {
      if (!e.dataTransfer || !Array.from(e.dataTransfer.types).includes('Files')) return;
      e.preventDefault();
      dragDepth += 1;
      showDropzone();
    });
    document.addEventListener('dragover', (e) => {
      if (!e.dataTransfer || !Array.from(e.dataTransfer.types).includes('Files')) return;
      e.preventDefault();
      e.dataTransfer.dropEffect = 'copy';
    });
    document.addEventListener('dragleave', (e) => {
      if (!e.dataTransfer) return;
      dragDepth -= 1;
      if (dragDepth <= 0) hideDropzone();
    });
    document.addEventListener('drop', (e) => {
      if (!e.dataTransfer) return;
      e.preventDefault();
      hideDropzone();
      const files = e.dataTransfer.files;
      if (!files || files.length === 0) { showError(ERR_NO_FILE); return; }
      if (files.length > 1) { showError(ERR_NO_FILE); return; }
      loadFile(files[0]);
    });
  }

  /* ============================================================== */
  /* Bootstrap                                                       */
  /* ============================================================== */

  let resizeRaf = 0;
  function onResize() {
    if (resizeRaf) cancelAnimationFrame(resizeRaf);
    resizeRaf = requestAnimationFrame(() => {
      resizeRaf = 0;
      if (pageState.activeTab === 'timelines' && pageState.analysis) {
        renderActiveTab();
      }
    });
  }

  function init() {
    appEl = document.getElementById('app');
    pickerEl = /** @type {HTMLInputElement} */ (document.getElementById('picker'));
    reportEl = document.getElementById('report');
    errorEl = document.getElementById('error');
    tabStripEl = document.getElementById('tabstrip');
    loadedFileEl = document.getElementById('loaded-file');

    if (!appEl || !pickerEl || !reportEl || !errorEl || !tabStripEl) {
      // eslint-disable-next-line no-console
      console.error('visualizer: required mount points missing in index.html');
      return;
    }

    pickerEl.addEventListener('change', () => {
      const file = pickerEl.files && pickerEl.files[0];
      loadFile(file || null);
    });

    bindDragAndDrop();
    window.addEventListener('resize', onResize);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
