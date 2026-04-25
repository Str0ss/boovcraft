'use strict';

(() => {
  /* ============================================================== */
  /* visualizer entry point                                          */
  /* ============================================================== */

  /* ---------- module state ---------- */

  let currentAnalysis = null;
  /** @type {HTMLElement|null} */ let appEl = null;
  /** @type {HTMLInputElement|null} */ let pickerEl = null;
  /** @type {HTMLElement|null} */ let reportEl = null;
  /** @type {HTMLElement|null} */ let errorEl = null;

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

  /* ---------- utilities ---------- */

  /**
   * Format an in-game millisecond timestamp as a user-facing string.
   * Switches between m:ss and h:mm:ss based on total match duration.
   */
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

  /**
   * Validate the parsed JSON has the seven required top-level keys
   * with the right primitive shapes. Returns { ok, message? }.
   */
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

  /**
   * Construct an entity-name DOM element honoring the unknown marker.
   */
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
    currentAnalysis = null;
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
      renderReport(parsed);
    };
    reader.readAsText(file);
  }

  /* ---------- top-level renderer ---------- */

  function renderReport(analysis) {
    currentAnalysis = analysis;
    const durationMs = analysis.match.durationMs;

    const frag = document.createDocumentFragment();
    frag.appendChild(renderMatchHeader(analysis, durationMs));
    frag.appendChild(renderTeams(analysis, durationMs));
    frag.appendChild(renderChat(analysis.chat, durationMs));
    frag.appendChild(renderObservers(analysis.observers));

    reportEl.replaceChildren(frag);
    reportEl.hidden = false;
  }

  /* ---------- §match-header ---------- */

  function renderMatchHeader(analysis, durationMs) {
    const m = analysis.match;
    const settings = analysis.settings || {};
    const winnerLabel = m.winner === null ? 'Undetermined' : `Team ${m.winner.teamId}`;
    const winnerCls = m.winner === null ? 'outcome outcome--undetermined' : 'outcome outcome--winner';

    const map = analysis.map || {};
    const mapName = map.file || map.path || '(unknown map)';

    const header = el('section', { class: 'match-header' }, [
      el('div', { class: 'match-header-line' }, [
        el('span', { class: winnerCls, text: `Outcome: ${winnerLabel}` }),
        el('span', { class: 'sep', text: '·' }),
        el('span', { class: 'duration', text: `Duration ${formatTimeMs(durationMs, durationMs)}` }),
        el('span', { class: 'sep', text: '·' }),
        el('span', { class: 'gametype', text: `${m.gameType} — ${m.matchup}` }),
        el('span', { class: 'sep', text: '·' }),
        el('span', {
          class: 'mapname',
          text: mapName,
          title: map.path || mapName,
        }),
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
    return header;
  }

  function kvPair(label, value) {
    if (value == null || value === '') return [];
    return [
      el('dt', { text: label }),
      el('dd', { text: String(value) }),
    ];
  }

  /* ---------- §team grouping & player panels ---------- */

  function groupPlayersByTeam(players) {
    const map = new Map();
    for (const p of players) {
      const arr = map.get(p.teamId) || [];
      arr.push(p);
      map.set(p.teamId, arr);
    }
    return new Map([...map.entries()].sort((a, b) => a[0] - b[0]));
  }

  function renderTeams(analysis, durationMs) {
    const grouping = groupPlayersByTeam(analysis.players);
    const wrapper = el('section', { class: 'teams' });
    for (const [teamId, players] of grouping.entries()) {
      const isWinningTeam = players.length > 0 && players.every(p => p.isWinner);
      const teamHeaderText = isWinningTeam ? `Team ${teamId} — winners` : `Team ${teamId}`;
      const teamSection = el('section', { class: 'team' }, [
        el('h2', { class: isWinningTeam ? 'team-header team-header--winner' : 'team-header', text: teamHeaderText }),
      ]);
      const grid = el('div', { class: 'team-grid' });
      for (const p of players) {
        grid.appendChild(renderPlayerPanel(p, durationMs));
      }
      teamSection.appendChild(grid);
      wrapper.appendChild(teamSection);
    }
    return wrapper;
  }

  function renderPlayerPanel(player, durationMs) {
    const panel = el('article', {
      class: 'player-panel',
      style: { borderLeftColor: player.color || '#888' },
    });

    /* header line: name · race · APM · winner badge */
    const headerChildren = [
      el('span', { class: 'player-name', text: player.name }),
      el('span', { class: 'player-race', text: raceLabel(player) }),
      el('span', { class: 'player-apm', text: `${player.apm} APM` }),
    ];
    if (player.isWinner) {
      headerChildren.push(el('span', { class: 'badge--winner', text: 'Winner' }));
    }
    panel.appendChild(el('header', { class: 'player-panel-header' }, headerChildren));

    /* color-swatch + slot id annotation */
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
    panel.appendChild(renderProductionSection(player.production || {}, durationMs));
    panel.appendChild(renderHeroSection(player.heroes || [], durationMs));
    panel.appendChild(renderTransferSection(player.resourceTransfers || [], durationMs));
    panel.appendChild(renderTimeline(player, durationMs));
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

  function renderProductionSection(production, durationMs) {
    const wrapper = el('section', { class: 'panel-section production' }, [
      el('h3', { class: 'panel-section-title', text: 'Production' }),
    ]);
    for (const cat of PRODUCTION_CATEGORIES) {
      const sub = production[cat.key] || { order: [], summary: {} };
      const subSection = el('section', { class: `prod-cat prod-cat--${cat.key}` }, [
        el('h4', { class: 'prod-cat-title', text: `${cat.label} (${sub.order ? sub.order.length : 0})` }),
      ]);
      if (!sub.order || sub.order.length === 0) {
        subSection.appendChild(el('p', { class: 'empty-state', text: cat.emptyState }));
      } else {
        const ol = el('ol', { class: 'prod-list' });
        for (const entry of sub.order) {
          const li = el('li', {}, [
            el('span', { class: 'time', text: formatTimeMs(entry.timeMs, durationMs) }),
            ' — ',
            entityLabelEl(entry),
          ]);
          ol.appendChild(li);
        }
        subSection.appendChild(ol);
      }
      wrapper.appendChild(subSection);
    }
    return wrapper;
  }

  function renderHeroSection(heroes, durationMs) {
    const wrapper = el('section', { class: 'panel-section heroes' }, [
      el('h3', { class: 'panel-section-title', text: 'Heroes' }),
    ]);
    if (!heroes || heroes.length === 0) {
      wrapper.appendChild(el('p', { class: 'empty-state', text: 'No heroes used.' }));
      return wrapper;
    }
    for (const hero of heroes) {
      const heroBlock = el('section', { class: 'hero-block' });
      const heroHeader = el('h4', { class: 'hero-header' });
      heroHeader.appendChild(entityLabelEl(hero, 'span'));
      heroHeader.appendChild(document.createTextNode(` — Level ${hero.level}`));
      heroBlock.appendChild(heroHeader);

      if (!hero.abilityOrder || hero.abilityOrder.length === 0) {
        heroBlock.appendChild(el('p', { class: 'empty-state', text: 'No abilities learned.' }));
      } else {
        const ol = el('ol', { class: 'ability-list' });
        for (const ab of hero.abilityOrder) {
          const li = el('li', {}, [
            el('span', { class: 'time', text: formatTimeMs(ab.timeMs, durationMs) }),
            ' — ',
            entityLabelEl(ab),
            el('span', { class: 'ability-level', text: ` (L${ab.level})` }),
          ]);
          ol.appendChild(li);
        }
        heroBlock.appendChild(ol);
      }
      wrapper.appendChild(heroBlock);
    }
    return wrapper;
  }

  function renderTransferSection(transfers, durationMs) {
    const wrapper = el('section', { class: 'panel-section transfers' }, [
      el('h3', { class: 'panel-section-title', text: 'Resource transfers' }),
    ]);
    if (!transfers || transfers.length === 0) {
      wrapper.appendChild(el('p', { class: 'empty-state', text: 'No allied resource transfers.' }));
      return wrapper;
    }
    const ul = el('ul', { class: 'transfer-list' });
    for (const t of transfers) {
      const parts = [];
      if (t.gold) parts.push(`+${formatInt(t.gold)} gold`);
      if (t.lumber) parts.push(`+${formatInt(t.lumber)} lumber`);
      const amount = parts.length ? parts.join(', ') : '(empty transfer)';
      ul.appendChild(el('li', {}, [
        el('span', { class: 'time', text: formatTimeMs(t.timeMs, durationMs) }),
        ' → ',
        el('span', { class: 'recipient', text: t.toPlayerName }),
        ': ',
        el('span', { class: 'amount', text: amount }),
      ]));
    }
    wrapper.appendChild(ul);
    return wrapper;
  }

  /* ---------- §timeline ---------- */

  const SVG_NS = 'http://www.w3.org/2000/svg';

  const TIMELINE_LAYOUT = {
    width: 720,
    height: 200,
    leftMargin: 60,
    rightMargin: 14,
    topMargin: 10,
    rowHeight: 30,
    axisY: 170,
    rows: ['building', 'unit', 'upgrade', 'item', 'ability'],
    rowLabels: {
      building: 'Bldg',
      unit: 'Unit',
      upgrade: 'Upgr',
      item: 'Item',
      ability: 'Hero',
    },
    markerSize: 6,
    tickCount: 5,
  };

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

  function buildTimelineEvents(player) {
    const events = [];
    const prod = player.production || {};
    const pushFromOrder = (orderArr, category) => {
      if (!Array.isArray(orderArr)) return;
      for (const e of orderArr) {
        events.push({
          category,
          label: e.name,
          rawId: e.id,
          isUnknown: e.unknown === true,
          timeMs: e.timeMs,
        });
      }
    };
    pushFromOrder(prod.buildings && prod.buildings.order, 'building');
    pushFromOrder(prod.units && prod.units.order, 'unit');
    pushFromOrder(prod.upgrades && prod.upgrades.order, 'upgrade');
    pushFromOrder(prod.items && prod.items.order, 'item');
    if (Array.isArray(player.heroes)) {
      for (const hero of player.heroes) {
        if (!Array.isArray(hero.abilityOrder)) continue;
        for (const ab of hero.abilityOrder) {
          events.push({
            category: 'ability',
            label: ab.name,
            rawId: ab.id,
            isUnknown: ab.unknown === true,
            timeMs: ab.timeMs,
            heroLabel: hero.name,
            heroIsUnknown: hero.unknown === true,
            abilityOrdinal: ab.level,
          });
        }
      }
    }
    events.sort((a, b) => a.timeMs - b.timeMs);
    return events;
  }

  function timelineMarkerShape(event, x, y, color) {
    const size = TIMELINE_LAYOUT.markerSize;
    const fill = event.isUnknown ? 'none' : color;
    const stroke = event.isUnknown ? '#c0a060' : color;
    const strokeWidth = event.isUnknown ? 1.5 : 0.5;
    switch (event.category) {
      case 'building':
        return svgEl('rect', {
          x: x - size,
          y: y - size,
          width: size * 2,
          height: size * 2,
          fill,
          stroke,
          'stroke-width': strokeWidth,
          tabindex: '0',
          class: 'tl-marker tl-marker--building' + (event.isUnknown ? ' tl-marker--unknown' : ''),
        });
      case 'unit':
        return svgEl('circle', {
          cx: x,
          cy: y,
          r: size,
          fill,
          stroke,
          'stroke-width': strokeWidth,
          tabindex: '0',
          class: 'tl-marker tl-marker--unit' + (event.isUnknown ? ' tl-marker--unknown' : ''),
        });
      case 'upgrade':
        return svgEl('polygon', {
          points: `${x},${y - size} ${x - size},${y + size} ${x + size},${y + size}`,
          fill,
          stroke,
          'stroke-width': strokeWidth,
          tabindex: '0',
          class: 'tl-marker tl-marker--upgrade' + (event.isUnknown ? ' tl-marker--unknown' : ''),
        });
      case 'item':
        return svgEl('polygon', {
          points: `${x},${y + size} ${x - size},${y - size} ${x + size},${y - size}`,
          fill,
          stroke,
          'stroke-width': strokeWidth,
          tabindex: '0',
          class: 'tl-marker tl-marker--item' + (event.isUnknown ? ' tl-marker--unknown' : ''),
        });
      case 'ability': {
        // 5-point star
        const points = [];
        for (let i = 0; i < 10; i++) {
          const r = i % 2 === 0 ? size : size * 0.45;
          const angle = (Math.PI / 5) * i - Math.PI / 2;
          const px = x + Math.cos(angle) * r;
          const py = y + Math.sin(angle) * r;
          points.push(`${px.toFixed(2)},${py.toFixed(2)}`);
        }
        return svgEl('polygon', {
          points: points.join(' '),
          fill,
          stroke,
          'stroke-width': strokeWidth,
          tabindex: '0',
          class: 'tl-marker tl-marker--ability' + (event.isUnknown ? ' tl-marker--unknown' : ''),
        });
      }
      default:
        return svgEl('circle', { cx: x, cy: y, r: 2, fill: stroke });
    }
  }

  function timelineMarkerTooltip(event, durationMs) {
    const t = formatTimeMs(event.timeMs, durationMs);
    if (event.isUnknown) {
      return `${t} — ${event.rawId} (unknown entity)`;
    }
    if (event.category === 'ability') {
      const hero = event.heroIsUnknown ? `${event.heroLabel} [?]` : event.heroLabel;
      return `${t} — ${event.label} (${hero} L${event.abilityOrdinal})`;
    }
    return `${t} — ${event.label}`;
  }

  function renderTimeline(player, durationMs) {
    const L = TIMELINE_LAYOUT;
    const events = buildTimelineEvents(player);
    const axisWidth = L.width - L.leftMargin - L.rightMargin;
    const playerColor = player.color || '#888';

    const svg = svgEl('svg', {
      class: 'timeline',
      viewBox: `0 0 ${L.width} ${L.height}`,
      preserveAspectRatio: 'xMidYMid meet',
      role: 'img',
      'aria-label': `Timeline for ${player.name}`,
    });

    /* row guides + row labels */
    L.rows.forEach((cat, i) => {
      const y = L.topMargin + i * L.rowHeight + L.rowHeight / 2;
      svg.appendChild(svgEl('line', {
        x1: L.leftMargin,
        y1: y,
        x2: L.width - L.rightMargin,
        y2: y,
        class: 'tl-row-guide',
      }));
      svg.appendChild(svgEl('text', {
        x: L.leftMargin - 8,
        y: y + 4,
        'text-anchor': 'end',
        class: 'tl-row-label',
      }, [document.createTextNode(L.rowLabels[cat])]));
    });

    /* axis */
    svg.appendChild(svgEl('line', {
      x1: L.leftMargin,
      y1: L.axisY,
      x2: L.width - L.rightMargin,
      y2: L.axisY,
      class: 'tl-axis',
    }));

    for (let i = 0; i < L.tickCount; i++) {
      const ratio = i / (L.tickCount - 1);
      const x = L.leftMargin + ratio * axisWidth;
      const t = ratio * durationMs;
      svg.appendChild(svgEl('line', {
        x1: x, y1: L.axisY, x2: x, y2: L.axisY + 4,
        class: 'tl-tick',
      }));
      svg.appendChild(svgEl('text', {
        x, y: L.axisY + 16,
        'text-anchor': 'middle',
        class: 'tl-tick-label',
      }, [document.createTextNode(formatTimeMs(t, durationMs))]));
    }

    /* markers */
    const safeDuration = Math.max(1, durationMs);
    for (const event of events) {
      const ratio = Math.max(0, Math.min(1, event.timeMs / safeDuration));
      const x = L.leftMargin + ratio * axisWidth;
      const rowIndex = L.rows.indexOf(event.category);
      const y = L.topMargin + rowIndex * L.rowHeight + L.rowHeight / 2;
      const marker = timelineMarkerShape(event, x, y, playerColor);
      const title = svgEl('title', {});
      title.appendChild(document.createTextNode(timelineMarkerTooltip(event, durationMs)));
      marker.appendChild(title);
      svg.appendChild(marker);
    }

    return el('section', { class: 'panel-section timeline-section' }, [
      el('h3', { class: 'panel-section-title', text: `Timeline (${events.length})` }),
      svg,
    ]);
  }

  /* ---------- §chat ---------- */

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

  /* ---------- §observers ---------- */

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

  /* ---------- §drag-and-drop ---------- */

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
      if (!files || files.length === 0) {
        showError(ERR_NO_FILE);
        return;
      }
      if (files.length > 1) {
        showError(ERR_NO_FILE);
        return;
      }
      loadFile(files[0]);
    });
  }

  /* ---------- bootstrap ---------- */

  function init() {
    appEl = document.getElementById('app');
    pickerEl = /** @type {HTMLInputElement} */ (document.getElementById('picker'));
    reportEl = document.getElementById('report');
    errorEl = document.getElementById('error');

    if (!appEl || !pickerEl || !reportEl || !errorEl) {
      // eslint-disable-next-line no-console
      console.error('visualizer: required mount points missing in index.html');
      return;
    }

    pickerEl.addEventListener('change', () => {
      const file = pickerEl.files && pickerEl.files[0];
      loadFile(file || null);
    });

    bindDragAndDrop();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
