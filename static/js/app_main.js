    // --- FULLSCREEN IMAGE LIGHTBOX ---
    function openImageLightbox(src) {
      if (!src) return;
      const modal = document.getElementById("image-lightbox-modal");
      const img = document.getElementById("image-lightbox-img");
      if (modal && img) {
        img.src = src;
        modal.style.display = "flex";
      }
    }
    function closeImageLightbox(event) {
      if (event && event.target && event.target.id === "image-lightbox-img") return;
      const modal = document.getElementById("image-lightbox-modal");
      const img = document.getElementById("image-lightbox-img");
      if (modal) modal.style.display = "none";
      if (img) img.src = "";
    }
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeImageLightbox();
    });

    let noticeTimer;
    function showNotice(message, type = 'success') {
      let notice = document.getElementById('app-notice');
      if (!notice) {
        notice = document.createElement('div');
        notice.id = 'app-notice';
        notice.className = 'app-notice';
        notice.setAttribute('role', 'status');
        document.body.appendChild(notice);
      }
      notice.textContent = message;
      notice.classList.toggle('error', type === 'error');
      notice.style.display = 'block';
      clearTimeout(noticeTimer);
      noticeTimer = setTimeout(() => { notice.style.display = 'none'; }, type === 'error' ? 6500 : 2800);
    }

    let _confirmResolve = null;
    function openConfirmDialog(message, title = "ยืนยันการทำรายการ", okText = "ยืนยัน", cancelText = "ยกเลิก") {
      return new Promise(resolve => {
        _confirmResolve = resolve;
        const modal = document.getElementById("confirm-dialog-modal");
        const titleEl = document.getElementById("confirm-modal-title");
        const msgEl = document.getElementById("confirm-modal-message");
        const okBtn = document.getElementById("confirm-modal-ok-btn");
        const cancelBtn = document.getElementById("confirm-modal-cancel-btn");
        if (titleEl) titleEl.innerHTML = `<span>⚠️</span><span>${escapeHtml(title)}</span>`;
        if (msgEl) msgEl.textContent = message;
        if (okBtn) okBtn.textContent = okText;
        if (cancelBtn) cancelBtn.textContent = cancelText;
        if (modal) modal.style.display = "flex";
        setTimeout(() => okBtn?.focus(), 50);
      });
    }
    function _closeConfirmModal(result) {
      const modal = document.getElementById("confirm-dialog-modal");
      if (modal) modal.style.display = "none";
      if (_confirmResolve) {
        const res = _confirmResolve;
        _confirmResolve = null;
        res(!!result);
      }
    }
    document.addEventListener("keydown", e => {
      if (e.key === "Escape" && document.getElementById("confirm-dialog-modal")?.style.display === "flex") {
        _closeConfirmModal(false);
      }
    });

    function updateMobilePaneScrim() {
      const open = document.querySelector('.sub-sidebar.mobile-open, .right-pane-container.mobile-open');
      document.getElementById('mobile-pane-scrim')?.classList.toggle('active', !!open);
    }
    function closeMobilePanes() {
      document.querySelector('.sub-sidebar')?.classList.remove('mobile-open');
      document.getElementById('right-pane-container')?.classList.remove('mobile-open');
      document.getElementById('chat-info-button')?.setAttribute('aria-expanded', 'false');
      updateMobilePaneScrim();
    }
    // `100dvh` in the mobile stylesheet follows the visible viewport on
    // current Android and iOS browsers.  Avoid JavaScript viewport listeners
    // here: they fire repeatedly during software-keyboard animation and can
    // make the focused composer lose its keyboard.
    function setupPullToRefresh() {
      const indicator = document.getElementById("pull-refresh-indicator");
      const label = document.getElementById("pull-refresh-label");
      if (!indicator || !label) return;
      const threshold = 86;
      let startX = 0, startY = 0, distance = 0, tracking = false, refreshing = false;

      const hasScrolledAncestor = target => {
        for (let node = target instanceof Element ? target : target?.parentElement; node && node !== document.body; node = node.parentElement) {
          const style = getComputedStyle(node);
          if (/(auto|scroll)/.test(style.overflowY) && node.scrollHeight > node.clientHeight + 1 && node.scrollTop > 0) return true;
        }
        return false;
      };
      const reset = () => {
        tracking = false;
        distance = 0;
        indicator.classList.remove("visible", "ready");
        indicator.style.transform = "translate(-50%, -70px)";
        label.textContent = "Pull down to refresh";
      };

      document.addEventListener("touchstart", event => {
        if (refreshing || window.innerWidth > 720 || event.touches.length !== 1) return;
        if (event.target.closest("input, textarea, select, [contenteditable='true']") || hasScrolledAncestor(event.target)) return;
        startX = event.touches[0].clientX;
        startY = event.touches[0].clientY;
        distance = 0;
        tracking = true;
      }, { passive:true });

      document.addEventListener("touchmove", event => {
        if (!tracking || refreshing || event.touches.length !== 1) return;
        const deltaX = event.touches[0].clientX - startX;
        const deltaY = event.touches[0].clientY - startY;
        if (deltaY <= 0 || Math.abs(deltaX) > deltaY) { reset(); return; }
        distance = Math.min(130, deltaY * .72);
        if (distance < 8) return;
        event.preventDefault();
        indicator.classList.add("visible");
        indicator.classList.toggle("ready", distance >= threshold);
        indicator.style.transform = `translate(-50%, ${Math.min(24, -42 + distance * .6)}px)`;
        label.textContent = distance >= threshold ? "ปล่อยเพื่อรีเฟรช" : "Pull down to refresh";
      }, { passive:false });

      const finish = () => {
        if (!tracking || refreshing) return;
        if (distance < threshold) { reset(); return; }
        refreshing = true;
        tracking = false;
        indicator.classList.remove("ready");
        indicator.classList.add("visible", "refreshing");
        indicator.style.transform = "translate(-50%, 14px)";
        label.textContent = "กำลังรีเฟรช…";
        setTimeout(() => window.location.reload(), 180);
      };
      document.addEventListener("touchend", finish, { passive:true });
      document.addEventListener("touchcancel", reset, { passive:true });
    }
    setupPullToRefresh();
    // A tab keeps its own account. Move an older shared-browser login once.
    let token = sessionStorage.getItem("realmplay_token") || localStorage.getItem("realmplay_token");
    let currentUser = sessionStorage.getItem("realmplay_user") || localStorage.getItem("realmplay_user");
    if (token && currentUser) {
      sessionStorage.setItem("realmplay_token", token);
      sessionStorage.setItem("realmplay_user", currentUser);
    }
    localStorage.removeItem("realmplay_token");
    localStorage.removeItem("realmplay_user");
    let activeCharacter = null;
    let characters = [];

    let currentDisplayName = "";
    let currentPersona = "";
    let currentHistory = [];
    let messageSelectionMode = false;
    let selectedMessageIndices = new Set();
    const messageAudioCache = new Map();
    let ttsAutoloadEnabled = false;
    let ttsAutoplayEnabled = false;
    let activeTtsController = null;
    let activeTtsAudio = null;
    window.addEventListener("rp-stop-voice", () => {
      activeTtsController?.abort();
      activeTtsController = null;
      if (activeTtsAudio) {
        activeTtsAudio.pause();
        activeTtsAudio.currentTime = 0;
        activeTtsAudio = null;
      }
    });
    let attachedVisionBase64 = null;
    let editingCharName = null;
    let newCharAvatarBase64 = null;
    let isRightPaneEditing = false;

    // 12 Items for the 3*4 Grid Outfits (with catalog slot mapping)
    const OUTFIT_GRID_ITEMS = [
      { id: "outer", label: "outer", icon: "🧥", isClothing: true, catalogSlot: "outer" },
      { id: "head", label: "head", icon: "👒", isClothing: false, catalogSlot: "head" },
      { id: "head_acc", label: "head acc", icon: "🎀", isClothing: false, catalogSlot: "accessories" },
      { id: "top", label: "top", icon: "👕", isClothing: true, catalogSlot: "top" },
      { id: "top_inner", label: "top inner", icon: "👙", isClothing: true, catalogSlot: "top_inner" },
      { id: "neck_acc", label: "neck acc", icon: "📿", isClothing: false, catalogSlot: "neck" },
      { id: "bottom", label: "bottom", icon: "👖", isClothing: true, catalogSlot: "bottom" },
      { id: "bottom_inner", label: "bottom inner", icon: "🩲", isClothing: true, catalogSlot: "bottom_inner" },
      { id: "hand_acc", label: "hand acc", icon: "🧤", isClothing: false, catalogSlot: "hands" },
      { id: "shoes", label: "Shoes", icon: "👠", isClothing: false, catalogSlot: "shoes" },
      { id: "socks", label: "stockings/socks", icon: "🧦", isClothing: false, catalogSlot: "socks" },
      { id: "leg_acc", label: "leg acc", icon: "🎗️", isClothing: false, catalogSlot: "accessories" }
    ];

    const CLOTHING_PART_KEYS = ["outer", "top", "top_inner", "bottom", "bottom_inner"];
    let currentWardrobe = {};
    let currentInventory = [];

    // --- INITIALIZATION ---
    window.onload = async () => {
      initProfileCardCollapsibles();
      if ((token && currentUser && await fetchUserProfile()) || await fetchUserProfile()) {
        document.getElementById("auth-screen").style.display = "none";
        await loadCharacters();
        await syncVoiceSettingsUI();
        startStatusPolling();
        return;
      }
      token = null;
      currentUser = null;
      sessionStorage.removeItem("realmplay_token");
      sessionStorage.removeItem("realmplay_user");
      document.getElementById("auth-screen").style.display = "flex";
    };

    // Close user dropdown if clicked outside
    document.addEventListener("click", (e) => {
      const menu = document.getElementById("user-dropdown-menu");
      const btn = document.getElementById("user-profile-btn");
      if (menu && btn && !btn.contains(e.target) && !menu.contains(e.target)) {
        menu.style.display = "none";
        btn.setAttribute("aria-expanded", "false");
      }
    });

    function toggleUserDropdown(e) {
      if (e) e.stopPropagation();
      const menu = document.getElementById("user-dropdown-menu");
      if (!menu) return;
      menu.style.display = menu.style.display === "flex" ? "none" : "flex";
      document.getElementById("user-profile-btn").setAttribute("aria-expanded", String(menu.style.display === "flex"));
    }

    // --- SLIM TABS SWITCHER ---
    function switchSlimTab(tabName) {
      const sidebar = document.querySelector('.sub-sidebar');
      const wasOpen = sidebar?.classList.contains('mobile-open');
      const wasActive = document.getElementById(`rail-btn-${tabName}`)?.classList.contains('active');
      const railBtns = ["characters", "textgen", "imagegen", "voicegen", "chatsettings", "features", "rules"];
      railBtns.forEach(b => {
        const btn = document.getElementById(`rail-btn-${b}`);
        if (btn) btn.classList.remove("active");
        const sub = document.getElementById(`subview-${b}`);
        if (sub) sub.style.display = "none";
      });

      const activeBtn = document.getElementById(`rail-btn-${tabName}`);
      if (activeBtn) activeBtn.classList.add("active");
      const activeSub = document.getElementById(`subview-${tabName}`);
      if (activeSub) activeSub.style.display = "flex";

      if (window.innerWidth <= 720) {
        document.getElementById('right-pane-container')?.classList.remove('mobile-open');
        sidebar?.classList.toggle('mobile-open', !(wasOpen && wasActive));
        updateMobilePaneScrim();
      }

      if (tabName === "textgen") {
        // Model choices are initialized by the configuration panel without resetting unsaved selection.
        syncProactiveSettings();
      } else if (tabName === "voicegen") {
        syncVoiceSettingsUI();
      } else if (tabName === "rules") {
        syncSlimRuleSettings();
      } else if (tabName === "features") {
        runRealmPlayAudit();
      }
    }

    // --- RIGHT PANE TABS SWITCHER ---
    function switchRightPaneTab(tabName) {
      const pillProfile = document.getElementById("pill-right-profile");
      const pillGallery = document.getElementById("pill-right-gallery");
      const tabProfile = document.getElementById("right-tab-profile");
      const tabGallery = document.getElementById("right-tab-gallery");

      if (tabName === "profile") {
        pillProfile.classList.add("active");
        pillGallery.classList.remove("active");
        tabProfile.style.display = "flex";
        tabGallery.style.display = "none";
      } else {
        pillGallery.classList.add("active");
        pillProfile.classList.remove("active");
        tabGallery.style.display = "flex";
        tabProfile.style.display = "none";
      }
    }

    function toggleRightPane() {
      const pane = document.getElementById("right-pane-container");
      if (pane) {
        if (window.innerWidth <= 960) {
          document.querySelector('.sub-sidebar')?.classList.remove('mobile-open');
          const open = pane.classList.toggle('mobile-open');
          document.getElementById('chat-info-button')?.setAttribute('aria-expanded', String(open));
          updateMobilePaneScrim();
          return;
        }
        pane.style.display = pane.style.display === "none" ? "flex" : "none";
      }
    }

    // --- RIGHT PANE EDIT MODE TOGGLE ---
    function toggleProfileCardSection(sectionId) {
      const el = document.getElementById(sectionId);
      if (!el) return;
      el.classList.toggle('collapsed');
      try {
        const isCollapsed = el.classList.contains('collapsed');
        localStorage.setItem('rp_section_collapsed_' + sectionId, isCollapsed ? '1' : '0');
      } catch (e) {}
    }

    function initProfileCardCollapsibles() {
      const sectionIds = [
        'section-boundaries',
        'section-realtime-state',
        'section-appearance',
        'section-outfits',
        'section-inventory',
        'section-situation',
        'section-memory'
      ];
      sectionIds.forEach(id => {
        try {
          if (localStorage.getItem('rp_section_collapsed_' + id) === '1') {
            document.getElementById(id)?.classList.add('collapsed');
          }
        } catch (e) {}
      });
    }

    function currentSituationDisplayValue(raw) {
      const fields = {};
      String(raw || '').split(/\r?\n/).forEach(line => {
        const match = line.match(/^\s*(Actor|Act|Target|Location|>Time)\s*:\s*(.*?)\s*$/i);
        if (match) fields[match[1].toLowerCase()] = match[2];
      });
      const route = [fields.actor, fields.act, fields.target].filter(Boolean).join(' → ');
      const context = [fields.location, fields['>time']].filter(value => value && value !== 'unchanged');
      return [route, ...context].filter(Boolean).join('\n') || String(raw || '');
    }

    function setSituationPane(raw) {
      const pane = document.getElementById('pane-input-situation');
      if (!pane) return;
      pane.dataset.canonicalScenario = String(raw || '');
      pane.value = pane.readOnly ? currentSituationDisplayValue(raw) : String(raw || '');
    }

    function situationPaneValueForSave() {
      const pane = document.getElementById('pane-input-situation');
      if (!pane) return '';
      const value = pane.readOnly ? (pane.dataset.canonicalScenario || '') : pane.value;
      pane.dataset.canonicalScenario = value;
      return value;
    }

    // "all must be use Edit button before edit and save to close edit"
    async function toggleRightPaneEditMode() {
      if (!activeCharacter) {
        alert("กรุณาPlease select a character firstแก้ไข");
        return;
      }

      const btn = document.getElementById("right-edit-toggle-btn");
      const profileInput = document.getElementById("pane-input-char-profile");
      const statusInput = document.getElementById("pane-input-status");
      const appearanceInput = document.getElementById("pane-input-appearance");
      const memoryInput = document.getElementById("pane-input-memory");

      if (!isRightPaneEditing) {
        // Turn ON Edit mode
        isRightPaneEditing = true;
        btn.innerText = "💾 Save Profile";
        btn.classList.add("editing");

        if (profileInput) profileInput.readOnly = false;
        statusInput.readOnly = false;
        appearanceInput.readOnly = false;
        memoryInput.readOnly = false;
        const situationInput = document.getElementById("pane-input-situation");
        situationInput.readOnly = false;
        situationInput.value = situationInput.dataset.canonicalScenario || situationInput.value;

        document.getElementById("character-profile-image-tools").hidden = false;
        if (profileInput) profileInput.focus(); else statusInput.focus();
        renderOutfits3x4Grid(currentWardrobe);
      } else {
        // Save and Turn OFF Edit mode
        await saveRightPaneAll();
        isRightPaneEditing = false;
        btn.innerText = "✏️ Edit Profile";
        btn.classList.remove("editing");

        if (profileInput) profileInput.readOnly = true;
        statusInput.readOnly = true;
        appearanceInput.readOnly = true;
        memoryInput.readOnly = true;
        const situationInput = document.getElementById("pane-input-situation");
        situationInput.readOnly = true;
        setSituationPane(situationInput.dataset.canonicalScenario || situationInput.value);
        document.getElementById("character-profile-image-tools").hidden = true;
        renderOutfits3x4Grid(currentWardrobe);
      }
    }

    async function saveRightPaneAll() {
      if (!activeCharacter) return;
      const profileVal = document.getElementById("pane-input-char-profile") ? document.getElementById("pane-input-char-profile").value : "";
      const statusVal = document.getElementById("pane-input-status").value;
      const appearVal = document.getElementById("pane-input-appearance").value;
      const memoryVal = document.getElementById("pane-input-memory").value;

      try {
        // 1. Save user state (status, memory, character_profile)
        await fetch(`/api/characters/${encodeURIComponent(activeCharacter)}/state`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({
            character_name: activeCharacter,
            character_profile: profileVal,
            status: statusVal,
            scenario: situationPaneValueForSave(),
            memory: memoryVal,
            appearance: appearVal
          })
        });

        // 2. Save wardrobe outfits
        await fetch(`/api/characters/${encodeURIComponent(activeCharacter)}/outfits`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({
            outfits: currentWardrobe
          })
        });

        showNotice(`บันทึกข้อมูลของ ${activeCharacter} แล้ว`);
      } catch (err) {
        showNotice("บันทึกไม่สำเร็จ: " + err.message, "error");
      }
    }

    // --- STATUS POLLING (3 colored dots with tooltip) ---
    let statusPollTimer = null;
    function startStatusPolling() {
      if (statusPollTimer) clearInterval(statusPollTimer);
      pollAllServiceStatus();
      statusPollTimer = setInterval(pollAllServiceStatus, 10000);
    }

    async function pollAllServiceStatus() {
      if (document.visibilityState !== "visible") return;
      try {
        const res = await fetch("/api/status/all", {
          headers: { "Authorization": `Bearer ${token}` }
        });
        if (!res.ok) return;
        const st = await res.json();

        // 1. LLM Engine Dot
        const eng = st.engine || {};
        const engDot = document.getElementById("top-dot-engine");
        const engTip = document.getElementById("tooltip-engine");
        if (engDot && engTip) {
          engDot.className = "status-dot";
          if (eng.state === "ready") {
            engDot.classList.add("green");
            engTip.innerText = `Engine: Ready (${eng.model || 'Loaded'}) Port ${eng.port || 5006}`;
          } else if (eng.state === "loading") {
            engDot.classList.add("yellow");
            engTip.innerText = `Engine: Loading model...`;
          } else if (eng.state === "error") {
            engDot.classList.add("red");
            engTip.innerText = `Engine: Error (${eng.error || 'Check logs'})`;
          } else {
            engTip.innerText = `Engine: Stopped`;
          }
        }

        // 2. ComfyUI Dot
        const comfy = st.comfy || {};
        const comfyDot = document.getElementById("top-dot-comfy");
        const comfyTip = document.getElementById("tooltip-comfy");
        const comfyStatusDot = document.getElementById("comfy-status-indicator");
        const comfyStatusText = document.getElementById("comfy-status-text");
        const comfyStatusDetails = document.getElementById("comfy-status-details");
        if (comfyDot && comfyTip) {
          comfyDot.className = "status-dot";
          if (comfy.connected) {
            comfyDot.classList.add("green");
            comfyTip.innerText = `ComfyUI: เชื่อมต่อสำเร็จ (${comfy.address || '8188'})`;
          } else {
            comfyTip.innerText = `ComfyUI: ออฟไลน์ / ไม่ได้เปิด`;
          }
        }
        if (comfyStatusDot && comfyStatusText && comfyStatusDetails) {
          comfyStatusDot.style.background = comfy.connected ? "#10b981" : "#64748b";
          comfyStatusText.textContent = comfy.connected ? "🟢 เชื่อมต่อแล้ว" : "⚪ ออฟไลน์ / ไม่ได้เปิด";
          comfyStatusDetails.textContent = comfy.address || "http://127.0.0.1:8188";
        }

        // 3. Voice Dot
        const voice = st.voice || {};
        const voiceDot = document.getElementById("top-dot-voice");
        const voiceTip = document.getElementById("tooltip-voice");
        const voiceStatusDot = document.getElementById("voice-status-indicator");
        const voiceStatusText = document.getElementById("voice-status-text");
        const voiceStatusDetails = document.getElementById("voice-status-details");
        if (voiceDot && voiceTip) {
          voiceDot.className = "status-dot";
          if (voice.rvc_enabled) {
            voiceDot.classList.add("green");
            voiceTip.innerText = `Voice: Edge-TTS + RVC Active (${voice.rvc_model ? voice.rvc_model.split(/[\\/]/).pop() : 'Loaded'})`;
          } else {
            voiceDot.classList.add("green");
            voiceTip.innerText = `Voice: Edge-TTS Ready`;
          }
        }
        if (voiceStatusDot && voiceStatusText && voiceStatusDetails) {
          voiceStatusDot.style.background = "#10b981";
          if (voice.rvc_enabled) {
            const modelName = voice.rvc_model ? voice.rvc_model.split(/[\\/]/).pop() : "ยังไม่ได้เลือกโมเดล";
            voiceStatusText.textContent = "🟢 Edge-TTS + RVC เปิดใช้งาน";
            voiceStatusDetails.textContent = `${voice.tts_voice || "Edge-TTS"} · RVC: ${modelName}`;
          } else {
            voiceStatusText.textContent = "🟢 Edge-TTS Ready";
            voiceStatusDetails.textContent = `${voice.tts_voice || "Edge-TTS"} · RVC ปิดอยู่`;
          }
        }

        // 4. Tunnel Access Dot & Menu
        const tun = st.tunnel || {};
        currentTunnelUrl = tun.url || null;
        const tunDot = document.getElementById("top-dot-tunnel");
        const tunTip = document.getElementById("tooltip-tunnel");
        const dropBadge = document.getElementById("drop-tunnel-badge");
        const dropRow = document.getElementById("drop-tunnel-row");
        const dropText = document.getElementById("drop-tunnel-url-text");
        const modalDot = document.getElementById("modal-tunnel-dot");
        const modalTxt = document.getElementById("modal-tunnel-status");
        const modalUrlBox = document.getElementById("modal-tunnel-url-box");
        const modalUrlText = document.getElementById("modal-tunnel-url-text");
        const btnStartTun = document.getElementById("btn-modal-start-tunnel");
        const btnStopTun = document.getElementById("btn-modal-stop-tunnel");

        if (tunDot && tunTip) {
          tunDot.className = "status-dot";
          if (tun.active) {
            tunDot.classList.add("blue");
            tunTip.innerText = `Tunnel: ${tun.url || 'Active (Port 8000)'} - คลิกเพื่อคัดลอก`;
          } else {
            tunTip.innerText = `Tunnel: Offline (คลิกเพื่อเริ่มแชร์ Remote Play)`;
          }
        }

        if (dropBadge) {
          if (tun.active) {
            dropBadge.innerText = "Online";
            dropBadge.style.color = "#38bdf8";
            dropBadge.style.background = "rgba(56, 189, 248, 0.2)";
            if (dropRow && dropText && tun.url) {
              dropRow.style.display = "flex";
              dropText.innerText = tun.url;
            }
          } else {
            dropBadge.innerText = "Offline";
            dropBadge.style.color = "#94a3b8";
            dropBadge.style.background = "rgba(255, 255, 255, 0.08)";
            if (dropRow) dropRow.style.display = "none";
          }
        }

        if (modalDot && modalTxt) {
          if (tun.active) {
            modalDot.style.background = "#38bdf8";
            modalTxt.innerText = "🟢 Online (Active)";
            if (modalUrlBox && modalUrlText && tun.url) {
              modalUrlBox.style.display = "flex";
              modalUrlText.innerText = tun.url;
            }
            if (btnStartTun) btnStartTun.disabled = true;
            if (btnStopTun) btnStopTun.disabled = false;
          } else {
            modalDot.style.background = "#64748b";
            modalTxt.innerText = "⚪ Offline (Stopped)";
            if (modalUrlBox) modalUrlBox.style.display = "none";
            if (btnStartTun) btnStartTun.disabled = false;
            if (btnStopTun) btnStopTun.disabled = true;
          }
        }

        updateEngineStatusUI(eng);
      } catch (e) {}
    }

    function updateEngineStatusUI(st) {
      const ind = document.getElementById("engine-status-indicator");
      const txt = document.getElementById("engine-status-text");
      const det = document.getElementById("engine-status-details");
      const btnStart = document.getElementById("rail-btn-start-engine");
      const btnStop = document.getElementById("rail-btn-stop-engine");

      if (!ind || !txt) return;
      if (st.state === "ready") {
        ind.style.background = "#10b981";
        txt.innerText = `🟢 Ready (${st.model || 'Loaded'})`;
        det.innerText = `Port ${st.port || 5006} (Vision: ${st.vision ? 'On' : 'Off'})`;
        if (btnStart) { btnStart.disabled = false; btnStart.innerText = "🔄 รีสตาร์ทโมเดล"; }
        if (btnStop) btnStop.disabled = false;
      } else if (st.state === "loading") {
        ind.style.background = "#f59e0b";
        txt.innerText = "🟡 Loading model...";
        det.innerText = "กำลังจัดสรร VRAM...";
        if (btnStart) { btnStart.disabled = true; btnStart.innerText = "⏳ กำลังโหลด..."; }
        if (btnStop) btnStop.disabled = false;
      } else if (st.state === "error") {
        ind.style.background = "#ef4444";
        txt.innerText = "🔴 Error";
        det.innerText = st.error || "ตรวจสอบ log";
        if (btnStart) { btnStart.disabled = false; btnStart.innerText = "▶ เริ่มใหม่"; }
        if (btnStop) btnStop.disabled = false;
      } else {
        ind.style.background = "#64748b";
        txt.innerText = "⚪ Stopped";
        det.innerText = `Port ${st.port || 5006}`;
        if (btnStart) { btnStart.disabled = false; btnStart.innerText = "▶ Start Engine"; }
        if (btnStop) btnStop.disabled = true;
      }
    }

    // --- USER PROFILE & AUTH ---
    async function fetchUserProfile() {
      try {
        const headers = token ? { "Authorization": `Bearer ${token}` } : {};
        const res = await fetch("/api/auth/me", { headers });
        if (!res.ok) {
          console.warn("fetchUserProfile /api/auth/me status:", res.status);
          return false;
        }
        const data = await res.json();
        if (data && data.username) {
          currentUser = data.username;
          currentDisplayName = data.display_name || "";
          currentPersona = data.persona || "";
          if (data.single_user_mode) {
            token = token || "single_user_token";
            sessionStorage.setItem("realmplay_user", currentUser);
            sessionStorage.setItem("realmplay_token", token);
          }

          const topUser = document.getElementById("top-user-name");
          if (topUser) topUser.innerText = currentDisplayName || currentUser;
          const dropDisp = document.getElementById("drop-display-name");
          if (dropDisp) dropDisp.innerText = currentDisplayName || `@${currentUser}`;
          const dropUser = document.getElementById("drop-username");
          if (dropUser) dropUser.innerText = `@${currentUser}`;
          const topAvatar = document.getElementById("top-user-avatar");
          if (topAvatar) topAvatar.src = `https://api.dicebear.com/7.x/bottts/svg?seed=${encodeURIComponent(currentUser)}`;

          const sideName = document.getElementById("sidebar-player-name");
          if (sideName) sideName.innerText = currentDisplayName || currentUser;
          const sideAvatar = document.getElementById("sidebar-player-avatar");
          if (sideAvatar) sideAvatar.src = `https://api.dicebear.com/7.x/bottts/svg?seed=${encodeURIComponent(currentUser)}`;

          const modalUser = document.getElementById("modal-username");
          if (modalUser) modalUser.value = `@${currentUser}`;
          const modalDisp = document.getElementById("modal-displayname");
          if (modalDisp) modalDisp.value = currentDisplayName;
          const modalPersona = document.getElementById("modal-persona");
          if (modalPersona) modalPersona.value = currentPersona;

          const adminItem = document.getElementById("drop-admin-item");
          if (adminItem) {
            adminItem.style.display = data.is_admin ? "flex" : "none";
          }

          if (data.rewards) {
            updatePlayerRewardsUI(data.rewards);
          }

          try { if (typeof loadUserImages === 'function') loadUserImages().catch(console.error); } catch (_) {}
          try { if (typeof loadChatDisplaySettings === 'function') loadChatDisplaySettings().catch(console.error); } catch (_) {}
          return true;
        }
      } catch (e) {
        console.error("fetchUserProfile failed:", e);
      }
      return false;
    }

    function openUserProfileModal() {
      const modal = document.getElementById("user-profile-modal");
      if (modal) modal.style.display = "flex";
      loadUserImages().catch(console.error);
      loadProfileImageDefaults().catch(console.error);
    }
    function closeUserProfileModal() {
      const modal = document.getElementById("user-profile-modal");
      if (modal) modal.style.display = "none";
    }
    function closeProfileModalOnBackdrop(e) {
      if (e.target.id === "user-profile-modal") closeUserProfileModal();
    }
    async function saveUserProfileModal() {
      const dispInput = document.getElementById("modal-displayname");
      const personaInput = document.getElementById("modal-persona");
      const newDisp = dispInput ? dispInput.value.trim() : "";
      const newPersona = personaInput ? personaInput.value.trim() : "";

      try {
        const res = await fetch("/api/auth/profile", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({ display_name: newDisp, persona: newPersona })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "ไม่สามารถบันทึกได้");
        currentDisplayName = data.display_name || "";
        currentPersona = data.persona || "";
        const topUser = document.getElementById("top-user-name");
        if (topUser) topUser.innerText = currentDisplayName || currentUser;
        const dropDisp = document.getElementById("drop-display-name");
        if (dropDisp) dropDisp.innerText = currentDisplayName || `@${currentUser}`;
        const sideName = document.getElementById("sidebar-player-name");
        if (sideName) sideName.innerText = currentDisplayName || currentUser;
        closeUserProfileModal();
        showNotice("บันทึกข้อมูลผู้ใช้แล้ว");
      } catch (e) {
        showNotice("บันทึกไม่สำเร็จ: " + e.message, "error");
      }
    }

    async function handleLogin() {
      const u = document.getElementById("auth-username").value.trim();
      const p = document.getElementById("auth-password").value;
      const errBox = document.getElementById("auth-error");
      errBox.style.display = "none";

      try {
        const res = await fetch("/api/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username: u, password: p })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || data.error);

        token = data.token;
        currentUser = data.username;
        currentDisplayName = data.display_name || "";
        sessionStorage.setItem("realmplay_token", token);
        sessionStorage.setItem("realmplay_user", currentUser);
        activeCharacter = null;
        characters = [];
        currentHistory = [];

        if (!await fetchUserProfile()) throw new Error("ตรวจสอบเซสชันไม่สำเร็จ กรุณาลองเข้าสู่ระบบอีกครั้ง");
        document.getElementById("auth-screen").style.display = "none";
        await loadCharacters();
        await syncVoiceSettingsUI();
        startStatusPolling();
      } catch (err) {
        token = null;
        currentUser = null;
        sessionStorage.removeItem("realmplay_token");
        sessionStorage.removeItem("realmplay_user");
        errBox.innerText = err.message;
        errBox.style.display = "block";
      }
    }

    function showRegistrationForm(show) {
      document.getElementById("login-box").style.display = show ? "none" : "block";
      document.getElementById("registration-box").style.display = show ? "block" : "none";
      document.getElementById("registration-result").style.display = "none";
    }

    async function handleRegister() {
      const username = document.getElementById("registration-id").value.trim();
      const email = document.getElementById("registration-email").value.trim();
      const result = document.getElementById("registration-result");
      result.style.display = "none";
      try {
        const response = await fetch("/api/auth/registration-request", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, email })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || data.error || "ส่งคำขอไม่สำเร็จ");
        result.textContent = data.message;
        result.style.color = "#86efac";
      } catch (error) {
        result.textContent = error.message;
        result.style.color = "#f87171";
      }
      result.style.display = "block";
    }

    async function handleLogout() {
      try {
        if (token) await fetch("/api/auth/logout", { method: "POST", headers: { "Authorization": `Bearer ${token}` } });
      } catch (error) { console.warn("Logout request failed:", error); }
      sessionStorage.removeItem("realmplay_token");
      sessionStorage.removeItem("realmplay_user");
      token = null;
      currentUser = null;
      location.reload();
    }



    function cardImageFallback(name) {
      return `https://api.dicebear.com/7.x/bottts/svg?seed=${encodeURIComponent(name || 'rp')}`;
    }
    async function loadCharacterPaneProfileImage(name) {
      const image = document.getElementById("pane-cover-avatar");
      if (!image) return;
      const encoded = encodeURIComponent(name);
      image.onerror = () => { image.onerror = null; image.src = cardImageFallback(name); };
      image.src = `/api/characters/${encoded}/avatar?cb=${Date.now()}`;
    }
    async function uploadCharacterProfileImage(input) {
      const file = input.files?.[0];
      if (!file || !activeCharacter) return;
      const body = new FormData(); body.append("file", file);
      try {
        const res = await fetch(`/api/characters/${encodeURIComponent(activeCharacter)}/profile-image`, {method:"POST", headers:{Authorization:`Bearer ${token}`}, body});
        const data = await res.json(); if (!res.ok) throw new Error(data.detail || "Upload failed");
        await refreshCardImages(); showNotice("อัปเดตรูปตัวละครแล้ว");
      } catch (err) { showNotice(err.message, "error"); }
      finally { input.value = ""; }
    }
    function getActiveWardrobePrompt() {
      const tags = [];
      const anyClothes = isAnyClothingOn(currentWardrobe);
      if (!anyClothes) {
        const nakedPrompt = (currentWardrobe.naked && currentWardrobe.naked.prompt) ? currentWardrobe.naked.prompt.trim() : "naked";
        if (nakedPrompt) tags.push(nakedPrompt);
      }
      for (const [k, v] of Object.entries(currentWardrobe)) {
        if (k === "naked") continue;
        if (v && v.active && v.prompt && v.prompt.trim()) {
          const p = v.prompt.trim();
          if (!tags.includes(p)) tags.push(p);
        }
      }
      return tags.join(", ");
    }
    async function openCharacterProfileGenerateDialog() {
      if (!activeCharacter) return;
      const appearance = (document.getElementById("pane-input-appearance")?.value || "").trim();
      const wardrobe = getActiveWardrobePrompt();
      const positiveParts = [appearance, wardrobe].filter(Boolean);
      const positiveInput = document.getElementById("character-profile-positive");
      if (positiveInput) {
        positiveInput.value = positiveParts.join(", ");
      }

      // Prefill Negative prompt from ComfyUI Image Gen configuration
      const negativeInput = document.getElementById("character-profile-negative");
      if (negativeInput) {
        const domNegative = document.getElementById("rp-negative_prompt")?.value?.trim();
        if (domNegative) {
          negativeInput.value = domNegative;
        } else if (window.rp?.config?.comfy?.negative_prompt) {
          negativeInput.value = window.rp.config.comfy.negative_prompt;
        } else {
          try {
            const res = await fetch("/api/configuration", { headers: { "Authorization": `Bearer ${token}` } });
            if (res.ok) {
              const cfg = await res.json();
              if (cfg?.comfy?.negative_prompt) {
                negativeInput.value = cfg.comfy.negative_prompt;
              }
            }
          } catch (e) {
            console.warn("Failed to fetch comfy negative_prompt:", e);
          }
        }
      }

      document.getElementById("character-profile-image-modal").style.display = "flex";
      document.getElementById("character-profile-positive").focus();
    }
    function closeCharacterProfileGenerateDialog() { document.getElementById("character-profile-image-modal").style.display = "none"; }
    function closeCharacterProfileGenerateDialogOnBackdrop(event) { if (event.target.id === "character-profile-image-modal") closeCharacterProfileGenerateDialog(); }
    async function generateCharacterProfileImage(button) {
      if (!activeCharacter) return;
      const positive = document.getElementById("character-profile-positive").value.trim();
      const negative = document.getElementById("character-profile-negative").value.trim();
      if (!positive) { showNotice("กรอก Positive prompt ก่อน", "error"); return; }
      const original = button.textContent; button.disabled = true; button.textContent = "⏳";
      try {
        const res = await fetch(`/api/characters/${encodeURIComponent(activeCharacter)}/profile-image/generate`, {method:"POST", headers:{"Content-Type":"application/json", Authorization:`Bearer ${token}`}, body:JSON.stringify({positive, negative})});
        const data = await res.json(); if (!res.ok) throw new Error(data.detail || "Generate failed");
        closeCharacterProfileGenerateDialog(); await refreshCardImages(); showNotice("สร้างรูปตัวละครแล้ว");
      } catch (err) { showNotice(err.message, "error"); }
      finally { button.disabled = false; button.textContent = original; }
    }
    async function deleteCharacterProfileImage() {
      if (!activeCharacter) return;
      if (!await openConfirmDialog("ลบ Character Profile Image นี้หรือไม่?", "ยืนยันการลบรูปโปรไฟล์")) return;
      try {
        const res = await fetch(`/api/characters/${encodeURIComponent(activeCharacter)}/profile-image`, {method:"DELETE", headers:{Authorization:`Bearer ${token}`}});
        const data = await res.json(); if (!res.ok) throw new Error(data.detail || "Delete failed");
        await refreshCardImages(); showNotice("ลบรูปตัวละครแล้ว");
      } catch (err) { showNotice(err.message, "error"); }
    }
    async function openCardViewer() {
      if (!activeCharacter) return;
      document.querySelector(".sub-sidebar")?.classList.add("card-viewing");
      document.getElementById("left-character-card-view").classList.add("open");
      document.querySelector("#subview-characters .sub-sidebar-header").style.display = "none";
      document.getElementById("char-list-container").style.display = "none";
      await loadCharacterCardViewer(activeCharacter);
      if (window.innerWidth <= 720) { document.querySelector(".sub-sidebar")?.classList.add("mobile-open"); updateMobilePaneScrim(); }
    }
    function closeCardViewer() {
      document.querySelector(".sub-sidebar")?.classList.remove("card-viewing");
      document.getElementById("left-character-card-view").classList.remove("open");
      document.querySelector("#subview-characters .sub-sidebar-header").style.display = "";
      document.getElementById("char-list-container").style.display = "";
    }
    document.addEventListener("pointerdown", event => {
      const panel = document.getElementById("left-character-card-view");
      if (panel?.classList.contains("open") && !panel.contains(event.target)) closeCardViewer();
    });
    function cardField(label, value) {
      return `<article class="character-card-field"><span class="character-card-field-label">${escapeHtml(label)}</span><div class="character-card-field-value">${escapeHtml(String(value || "—"))}</div></article>`;
    }
    async function openCharacterSummaryEditor() {
      if (!activeCharacter) { showNotice("Please select a character first", "error"); return; }
      const name = activeCharacter;
      const modal = document.getElementById("character-summary-modal");
      const input = document.getElementById("character-summary-input");
      modal.dataset.character = name;
      document.getElementById("character-summary-character-name").textContent = name;
      input.value = "Loading…";
      input.disabled = true;
      modal.style.display = "flex";
      try {
        const res = await fetch(`/api/characters/${encodeURIComponent(name)}/summary`, {headers:{Authorization:`Bearer ${token}`}});
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Cannot load Char_Summary.md");
        if (activeCharacter !== name) { closeCharacterSummaryEditor(); return; }
        input.value = data.summary || "";
        input.focus();
      } catch (err) {
        closeCharacterSummaryEditor();
        showNotice(err.message, "error");
      } finally { input.disabled = false; }
    }
    function closeCharacterSummaryEditor() { document.getElementById("character-summary-modal").style.display = "none"; }
    function closeCharacterSummaryEditorOnBackdrop(event) { if (event.target.id === "character-summary-modal") closeCharacterSummaryEditor(); }
    async function saveCharacterSummary() {
      const modal = document.getElementById("character-summary-modal");
      const name = modal.dataset.character;
      if (!name) return;
      const button = document.getElementById("character-summary-save");
      const input = document.getElementById("character-summary-input");
      const original = button.textContent;
      button.disabled = true; input.disabled = true; button.textContent = "Saving…";
      try {
        const res = await fetch(`/api/characters/${encodeURIComponent(name)}/summary`, {
          method:"PUT", headers:{"Content-Type":"application/json", Authorization:`Bearer ${token}`},
          body:JSON.stringify({summary:input.value})
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Cannot save Char_Summary.md");
        closeCharacterSummaryEditor();
        showNotice("บันทึก Char_Summary.md แล้ว");
      } catch (err) { showNotice(err.message, "error"); }
      finally { button.disabled = false; input.disabled = false; button.textContent = original; }
    }
    async function loadCharacterCardViewer(name) {
      const image = document.getElementById("left-card-avatar");
      image.onerror = () => { image.onerror = null; image.src = cardImageFallback(name); };
      image.src = `/api/characters/${encodeURIComponent(name)}/avatar?cb=${Date.now()}`;
      const box = document.getElementById("left-character-card-fields"); box.textContent = "Loading Character Card…";
      try {
        const res = await fetch(`/api/characters/${encodeURIComponent(name)}/card-document`, {headers:{Authorization:`Bearer ${token}`}});
        const doc = await res.json(); if (!res.ok) throw new Error(doc.detail || "Cannot load Character Card");
        const d = doc.data || doc;
        const fields = [["Name",d.name],["Description",d.description],["Personality",d.personality],["Scenario",d.scenario],["First Message",d.first_mes],["Example Messages",d.mes_example],["Creator Comment",d.creatorcomment],["Tags",Array.isArray(d.tags) ? d.tags.join(", ") : d.tags],["Talkativeness",d.talkativeness]];
        box.innerHTML = fields.map(([label,value]) => cardField(label,value)).join("");
        const summary = document.createElement("article");
        summary.className = "character-card-field";
        const summaryLabelRow = document.createElement("div");
        summaryLabelRow.className = "character-summary-label-row";
        const summaryLabel = document.createElement("span");
        summaryLabel.className = "character-card-field-label";
        summaryLabel.textContent = "Auto Summary · Char_Summary.md";
        const editSummary = document.createElement("button");
        editSummary.type = "button";
        editSummary.className = "btn btn-secondary character-summary-edit";
        editSummary.title = "Edit Char_Summary.md";
        editSummary.setAttribute("aria-label", "Edit Char_Summary.md");
        editSummary.textContent = "📝";
        editSummary.onclick = openCharacterSummaryEditor;
        const summaryValue = document.createElement("div");
        summaryValue.className = "character-card-field-value";
        summaryValue.textContent = doc.analysis?.summary_markdown || "No saved character summary available.";
        summaryLabelRow.append(summaryLabel, editSummary);
        summary.append(summaryLabelRow, summaryValue);
        box.appendChild(summary);
      } catch (err) { box.textContent = err.message; }
    }
    async function uploadCharacterCardImage(input) {
      const file=input.files?.[0]; if(!file || !activeCharacter) return;
      const body=new FormData(); body.append("file",file);
      try { const res=await fetch(`/api/characters/${encodeURIComponent(activeCharacter)}/avatar`,{method:"POST",headers:{Authorization:`Bearer ${token}`},body}); const data=await res.json(); if(!res.ok) throw new Error(data.detail||"Upload failed"); await refreshCardImages(); showNotice("อัปเดตรูป Character Card แล้ว"); } catch(err) { showNotice(err.message,"error"); } finally { input.value=""; }
    }
    async function deleteCharacterCardImage() {
      if(!activeCharacter) return;
      if(!await openConfirmDialog("ลบรูป Character Card นี้หรือไม่?", "ยืนยันการลบรูปการ์ด")) return;
      try { const res=await fetch(`/api/characters/${encodeURIComponent(activeCharacter)}/avatar`,{method:"DELETE",headers:{Authorization:`Bearer ${token}`}}); const data=await res.json(); if(!res.ok) throw new Error(data.detail||"Delete failed"); await refreshCardImages(); showNotice("ลบรูป Character Card แล้ว"); } catch(err) { showNotice(err.message,"error"); }
    }
    async function refreshCardImages() {
      if (!activeCharacter) return;
      const src=`/api/characters/${encodeURIComponent(activeCharacter)}/avatar?cb=${Date.now()}`;
      ["chat-header-avatar","left-card-avatar"].forEach(id=>{const el=document.getElementById(id); if(el) el.src=src;});
      renderCharacterList(); await loadCharacterPaneProfileImage(activeCharacter); await loadCharacterCardViewer(activeCharacter);
      const sprites = characters.find(c => c.name === activeCharacter)?.sprites || [];
      await loadCharacterGallery(activeCharacter, sprites);
    }
    function exportCurrentCharJSON() { if(activeCharacter) window.location.href=`/api/characters/${encodeURIComponent(activeCharacter)}/export-json`; }

    // --- CHARACTER MANAGEMENT ---
    async function loadCharacters() {
      try {
        const res = await fetch("/api/characters", {
          headers: { "Authorization": `Bearer ${token}` },
          cache: "no-store"
        });
        characters = await res.json();
        // Baseline unread totals on first load. Existing unread messages stay
        // visible as badges, but are not incorrectly announced as new SMS.
        if (typeof previousUnreadTotals === "object") {
          previousUnreadTotals = Object.fromEntries(characters.map(c => [c.name, c.unread_count || 0]));
        }
        renderCharacterList();
        // Starts with 1st character selected
        if (characters.length > 0 && !activeCharacter) {
          selectCharacter(characters[0].name);
        }
      } catch (e) {
        console.error("loadCharacters error:", e);
      }
    }

    function canDeleteCharactersGlobally() {
      return (currentUser || "").trim().toLowerCase() === "zarch";
    }

    async function deleteCharacterEverywhere(name) {
      if (!canDeleteCharactersGlobally()) return;
      const confirmed = await openConfirmDialog(
        `ลบ ${name} และประวัติของตัวละครนี้สำหรับผู้ใช้ทุกคนถาวรหรือไม่? การกระทำนี้ย้อนกลับไม่ได้`,
        "ยืนยันการลบตัวละคร",
        "ลบถาวร"
      );
      if (!confirmed) return;
      try {
        const res = await fetch(`/api/admin/characters/${encodeURIComponent(name)}`, {
          method: "DELETE",
          headers: { "Authorization": `Bearer ${token}` }
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Delete failed");
        if (activeCharacter === name) {
          activeCharacter = null;
          currentHistory = [];
        }
        await loadCharacters();
        showNotice(`ลบ ${name} และประวัติผู้ใช้ ${data.deleted_user_histories || 0} รายแล้ว`);
      } catch (err) {
        showNotice(err.message, "error");
      }
    }

    function formatChatListTime(timestamp) {
      if (!timestamp || timestamp <= 0) return "";
      const date = new Date(timestamp * 1000);
      if (isNaN(date.getTime())) return "";
      const now = new Date();
      const isToday = date.toDateString() === now.toDateString();
      if (isToday) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
      }
      const yesterday = new Date(now);
      yesterday.setDate(now.getDate() - 1);
      if (date.toDateString() === yesterday.toDateString()) {
        return "เมื่อวาน";
      }
      const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));
      if (diffDays < 7) {
        const days = ["อา.", "จ.", "อ.", "พ.", "พฤ.", "ศ.", "ส."];
        return days[date.getDay()];
      }
      return date.toLocaleDateString([], { day: 'numeric', month: 'short' });
    }

    function renderCharacterList(filterText = "") {
      filterText = document.getElementById("char-search-input")?.value.trim() || filterText;
      const container = document.getElementById("char-list-container");
      container.innerHTML = "";

      const filtered = [...characters].sort((a, b) => (b.last_message_at || 0) - (a.last_message_at || 0)).filter(c => 
        !filterText || c.name.toLowerCase().includes(filterText.toLowerCase())
      );

      filtered.forEach(c => {
        const div = document.createElement("div");
        div.className = `char-card-item ${activeCharacter === c.name ? 'active' : ''}`;
        div.onclick = () => selectCharacter(c.name);
        const hasUnread = (c.unread_count || 0) > 0;
        const timeStr = formatChatListTime(c.last_message_at);
        const snippetText = c.last_message || (c.persona || '').substring(0, 30);
        div.innerHTML = `
          <span class="char-card-avatar-frame"><img class="char-card-avatar" data-character-name="${escapeHtml(c.name)}" src="/api/characters/${encodeURIComponent(c.name)}/avatar" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${encodeURIComponent(c.name)}'"></span>
          <div class="char-card-info">
            <div class="char-card-row-top">
              <span class="char-card-name">${escapeHtml(c.name)}</span>
              ${timeStr ? `<span class="char-card-time">${escapeHtml(timeStr)}</span>` : ''}
              ${canDeleteCharactersGlobally() ? `<button type="button" class="char-delete-button" title="ลบตัวละครและประวัติของผู้ใช้ทุกคน" aria-label="ลบ ${escapeHtml(c.name)}">🗑</button>` : ''}
            </div>
            <div class="char-card-row-bottom">
              <span class="char-card-snippet ${hasUnread ? 'unread' : ''}">${escapeHtml(snippetText)}</span>
              ${hasUnread ? `<span class="chat-unread-badge" aria-label="${c.unread_count} unread messages">${c.unread_count > 99 ? '99+' : c.unread_count}</span>` : ''}
            </div>
          </div>
        `;
        const deleteButton = div.querySelector(".char-delete-button");
        if (deleteButton) {
          deleteButton.addEventListener("click", event => {
            event.preventDefault();
            event.stopPropagation();
            deleteCharacterEverywhere(c.name);
          });
        }
        container.appendChild(div);
      });
    }

    function filterCharacters(val) {
      renderCharacterList(val.trim());
    }

    function readArousalGauge() {
      const status = document.getElementById("pane-input-status")?.value || "";
      const numeric = status.match(/^\s*-?\s*Arousal\s*:\s*.*?\(?\s*(\d{1,3})\s*\/\s*100\s*\)?/im);
      if (numeric) return Math.max(0, Math.min(100, Number(numeric[1])));
      const label = (status.match(/^\s*-?\s*Arousal\s*:\s*([^\r\n]+)/im)?.[1] || "").toLowerCase();
      if (label.includes("overwhelmed")) return 100;
      if (label.includes("high")) return 75;
      if (label.includes("medium")) return 50;
      if (label.includes("low")) return 25;
      return 0;
    }

    let hEnergyCountdownTimer = null;
    function updateHEnergyRecoveryCountdown() {
      const target = document.getElementById("h-energy-recovery");
      if (!target) return;
      const energy = Number(target.dataset.energy || 0);
      if (energy >= 3) {
        target.style.color = "var(--text-muted)";
        target.style.fontWeight = "600";
        target.textContent = "Full";
        return;
      }
      const updatedAt = Number(target.dataset.updatedAt || 0) * 1000;
      const remainingSeconds = Math.max(0, Math.ceil(((updatedAt + 30 * 60 * 1000) - Date.now()) / 1000));
      const minutes = Math.floor(remainingSeconds / 60);
      const seconds = String(remainingSeconds % 60).padStart(2, "0");
      const timerTxt = remainingSeconds ? `+1 in ${minutes}:${seconds}` : "+1 ready";
      if (energy <= 0) {
        target.style.color = "#ef4444";
        target.style.fontWeight = "800";
        target.textContent = `Exhausted (${timerTxt})`;
      } else {
        target.style.color = "var(--text-muted)";
        target.style.fontWeight = "600";
        target.textContent = `${energy}/3 (${timerTxt})`;
      }
    }

    function renderHModeGauge(scene) {
      const host = document.getElementById("h-mode-gauge");
      if (!host) return;
      const state = scene || {stage:"normal", stage_level:0, h_energy:3, exhausted:false};
      const stage = state.stage || "normal";
      const level = Number(state.stage_level || 0);
      const romanLevel = ({1:"I", 2:"II", 3:"III"})[Math.max(1, Math.min(3, level))] || "I";
      const stageOffsets = {normal:0, intimacy:0, foreplay:3, explicit:6, climax:9, aftercare:12};
      const stagePosition = stage === "normal" ? 0 : Math.min(15, (stageOffsets[stage] ?? 0) + Math.max(1, Math.min(3, level)));
      const stagePercent = (stagePosition / 15) * 100;
      const stageBackgroundSize = stagePosition ? 1500 / stagePosition : 100;
      const stageColor = stage === "aftercare" ? "#e978ad" : `hsl(${Math.round(135 - stagePercent * .95)}, 76%, 51%)`;
      const scale = [
        ["Intimacy", 1.5], ["Foreplay", 4.5], ["Explicit", 7.5], ["Climax", 10.5], ["Aftercare", 13.5],
      ].map(([name, point]) => `<span style="position:absolute;left:${(point / 15) * 100}%;transform:translateX(-50%);font-size:9px;white-space:nowrap;color:${stage === name.toLowerCase() ? stageColor : 'var(--text-muted)'};font-weight:${stage === name.toLowerCase() ? '800' : '600'}">${name}</span>`).join("");
      const label = stage[0].toUpperCase() + stage.slice(1);
      const stageLabel = stage === "normal" ? label : `${label} ${romanLevel}`;
      const arousal = readArousalGauge();
      const arousalColor = `hsl(${Math.round(120 - arousal * 1.2)}, 78%, 48%)`;
      const hEnergy = Math.max(0, Math.min(3, Number(state.h_energy ?? 3)));
      const hQuest = state.h_mode_quest || state.active_quest || {};
      const questPending = Object.keys(hQuest).length > 0 && !["completed", "declined", "expired", "failed"].includes(hQuest.status);
      const questHint = questPending
        ? `H-Quest · รอการยืนยันเพื่อไป ${hQuest.target_stage || "stage ถัดไป"}`
        : (state.reason || "พิมพ์ ‘ต่อ’, ‘ช้าลง’, ‘เข้า Aftercare’ หรือ ‘จบฉาก’ ในแชต; ‘จบฉาก’ จะไป Aftercare เสมอ");
      const peakCounters = Array.from({length: 3}, (_, index) => {
        const available = index < hEnergy;
        return `<span aria-hidden="true" style="color:${available ? '#f6c344' : '#596174'};text-shadow:${available ? '0 0 7px rgba(246,195,68,.85)' : 'none'};font-size:15px;transition:color .25s ease">⚡</span>`;
      }).join("");
      const updatedAt = Number(state.h_energy_updated_at || 0) * 1000;
      host.innerHTML = `<div><div style="display:flex;align-items:center;gap:7px"><strong>Arousal</strong><span aria-label="H-Energy" title="H-Energy: ${hEnergy}/3; restores 1 point every 30 minutes" style="display:inline-flex;gap:1px;line-height:1">${peakCounters}</span><span id="h-energy-recovery" data-energy="${hEnergy}" data-updated-at="${Number(state.h_energy_updated_at || 0)}" style="font-size:10px;color:var(--text-muted);white-space:nowrap"></span><span style="margin-left:auto;color:${arousalColor};font-weight:800">${arousal}/100</span></div><div aria-label="Arousal gauge" title="Arousal ${arousal}/100" style="height:12px;overflow:hidden;border:1px solid #35394a;border-radius:999px;margin-top:6px;background:#202331"><div style="height:100%;width:${arousal}%;min-width:${arousal ? '5px' : '0'};background:linear-gradient(90deg,#2ecc71 0%,#b9d849 42%,#f39c3d 70%,#e74c3c 100%);box-shadow:0 0 8px ${arousalColor};transition:width .25s ease"></div></div></div><div style="margin-top:10px"><div style="display:flex;align-items:center"><strong style="color:${stageColor}">${label}</strong><span style="margin-left:auto;color:${stageColor};font-size:11px;font-weight:800">${stagePosition}/15</span></div><div aria-label="H-Mode stage progression" title="${label}: ${stagePosition}/15" style="height:13px;position:relative;overflow:hidden;border:1px solid #35394a;border-radius:999px;margin-top:6px;background:repeating-linear-gradient(90deg,#202331 0 calc((100% / 15) - 1px),#454a5d calc((100% / 15) - 1px) calc(100% / 15))"><div style="height:100%;width:${stagePercent}%;min-width:${stagePosition ? '5px' : '0'};background:repeating-linear-gradient(90deg,transparent 0 calc((100% / 15) - 1px),rgba(26,30,42,.55) calc((100% / 15) - 1px) calc(100% / 15)),linear-gradient(90deg,#2ecc71 0%,#2ecc71 13.333%,#b9d849 32%,#f39c3d 50%,#ff0000 58%,#ff0000 66.667%,#7f1d1d 80%,#e978ad 80%,#e978ad 100%);background-size:${stageBackgroundSize}% 100%,${stageBackgroundSize}% 100%;background-position:left top,left top;background-repeat:no-repeat,no-repeat;box-shadow:0 0 8px ${stageColor};transition:width .25s ease"></div></div><div style="height:16px;position:relative;margin-top:3px">${scale}</div></div><small style="color:${questPending ? "#d8ef76" : "var(--text-muted)"}">${questHint}</small>`;
      const stageHeading = host.querySelector(`strong[style*="color:${stageColor}"]`);
      if (stageHeading) stageHeading.textContent = stageLabel;
      updateHEnergyRecoveryCountdown();
      if (!hEnergyCountdownTimer) hEnergyCountdownTimer = window.setInterval(updateHEnergyRecoveryCountdown, 1000);
    }

    async function selectCharacter(name) {
      activeCharacter = name;
      const curChar = characters.find(c => c.name === name);
      if (curChar) {
        curChar.unread_count = 0;
        if (typeof previousUnreadTotals === 'object') {
          previousUnreadTotals[name] = 0;
        }
      }
      renderCharacterList();

      // Middle chat header
      document.getElementById("chat-header-name").innerText = name;
      const chatAvatar = document.getElementById("chat-header-avatar");
      chatAvatar.src = `/api/characters/${encodeURIComponent(name)}/avatar`;
      chatAvatar.style.display = "block";

      // Right pane cover
      document.getElementById("pane-cover-name").innerText = name;
      const coverAvatar = document.getElementById("pane-cover-avatar");
      loadCharacterPaneProfileImage(name).catch(console.error);

      // Load user isolated state
      const res = await fetch(`/api/characters/${encodeURIComponent(name)}/state`, {
        headers: { "Authorization": `Bearer ${token}` },
        cache: "no-store"
      });
      const data = await res.json();
      if (activeCharacter !== name) return;

      const charProfInput = document.getElementById("pane-input-char-profile");
      if (charProfInput) {
        charProfInput.value = data.character_profile || "";
      }
      document.getElementById("pane-input-status").value = statusWithMood(data.status, data.emotion);
      renderHModeGauge(data.scene_state);
      setSituationPane(data.scenario || "");
      document.getElementById("pane-input-memory").value = data.memory || "";
      const base = data.baseline || {};
      document.getElementById("pane-input-appearance").value = data.appearance || "";

      currentWardrobe = data.outfits || {};
      renderOutfits3x4Grid(currentWardrobe);
      currentInventory = Array.isArray(data.inventory) ? data.inventory : [];
      renderInventoryList(currentInventory);
      await loadCharacterGallery(name, base.sprites || []);
      renderChatHistory(data.history, true, true);
      await markVisibleChatRead(name, data.history);
      startProactivePresencePolling();
      if (window.innerWidth <= 720) closeMobilePanes();
    }

    // --- OUTFITS SYSTEM (1 TOP NAKED BUTTON + 12 ITEMS IN 3*4 GRID) ---
    function isAnyClothingOn(outfits) {
      return CLOTHING_PART_KEYS.some(k => {
        const it = outfits[k];
        return it && it.active && it.prompt && it.prompt.trim() !== "";
      });
    }

    function renderOutfits3x4Grid(outfits) {
      const grid = document.getElementById("outfits-grid-container");
      grid.innerHTML = "";

      const anyCloth = isAnyClothingOn(outfits);
      const isNakedActive = !anyCloth || !!(outfits.naked && outfits.naked.active);

      // Update Top Naked Button UI
      const nakedBtn = document.getElementById("btn-naked-toggle");
      const nakedTxt = document.getElementById("naked-btn-text");
      if (nakedBtn && nakedTxt) {
        if (isNakedActive) {
          nakedBtn.classList.add("active");
          nakedTxt.innerText = "Naked";
        } else {
          nakedBtn.classList.remove("active");
          nakedTxt.innerText = "Naked";
        }
      }

      // Render 12 items in 3x4 grid
      OUTFIT_GRID_ITEMS.forEach(part => {
        let item = outfits[part.id];
        if (!item) {
          item = { active: false, prompt: part.id };
          outfits[part.id] = item;
        }

        const isActive = !!item.active && !isNakedActive ? true : (part.isClothing ? false : !!item.active);
        const cell = document.createElement("div");
        cell.className = `outfit-grid-cell ${isActive ? 'active' : ''}`;
        cell.id = `outfit-cell-${part.id}`;

        // The name box is display-only. It must show an equipped item's name,
        // never an inventory/catalog choice or a placeholder slot name.
        const displayedItemName = isActive
          ? (item.name || ((item.prompt && item.prompt !== part.id) ? item.prompt : ""))
          : "";
        cell.innerHTML = `
          <div class="outfit-cell-head" onclick="toggleOutfitPart('${part.id}')">
            <span class="outfit-cell-label">${part.icon} ${part.label}</span>
          </div>
          <input type="text" class="outfit-cell-prompt" id="prompt-input-${part.id}"
            value="${escapeHtml(displayedItemName)}"
            readonly
            aria-label="Equipped ${part.label} item"
            placeholder="">
        `;
        grid.appendChild(cell);
      });
    }

    async function persistCurrentWardrobe() {
      if (!activeCharacter) return;
      try {
        await fetch(`/api/characters/${encodeURIComponent(activeCharacter)}/outfits`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({ outfits: currentWardrobe })
        });
      } catch (err) {
        console.warn("Failed to persist wardrobe toggle:", err);
      }
    }

    async function toggleNakedMode() {
      const anyCloth = isAnyClothingOn(currentWardrobe);
      const currentlyNaked = !anyCloth;

      // Wardrobe controls are scene actions, not silent state toggles. Route
      // them through chat so the character produces the corresponding action
      // narration and the server remains the source of durable state.
      const activeGarments = Object.entries(currentWardrobe)
        .filter(([key, value]) => key !== "naked" && value && value.active)
        .map(([key, value]) => value.name || value.prompt || key)
        .filter(Boolean);
      const actionText = currentlyNaked
        ? "*สวมเสื้อผ้ากลับตามปกติ*"
        : `*ถอด ${activeGarments.join(", ")} ออกจนเปลือย*`;
      const chatInput = document.getElementById("chat-input");
      if (chatInput && typeof sendMessage === "function") {
        chatInput.value = actionText;
        await sendMessage({ manualWardrobe: true });
        return;
      }

      if (!currentlyNaked) {
        // Turn ON Naked: turn off all clothing parts
        CLOTHING_PART_KEYS.forEach(k => {
          if (currentWardrobe[k]) currentWardrobe[k].active = false;
        });
        currentWardrobe["naked"] = { active: true, prompt: "naked, revealed breasts, revealed pussie, innie pussy, labia less" };
      } else {
        // Turn OFF Naked: turn on default outer/jacket
        if (!currentWardrobe["outer"]) {
          currentWardrobe["outer"] = { active: true, prompt: "casual clothes, jacket" };
        } else {
          currentWardrobe["outer"].active = true;
          if (!currentWardrobe["outer"].prompt) currentWardrobe["outer"].prompt = "casual clothes, jacket";
        }
        currentWardrobe["naked"] = { active: false, prompt: "naked" };
      }

      renderOutfits3x4Grid(currentWardrobe);
      await persistCurrentWardrobe();
    }

    async function toggleOutfitPart(partId) {
      if (!currentWardrobe[partId]) {
        currentWardrobe[partId] = { active: false, prompt: partId };
      }
      const item = currentWardrobe[partId];
      const nextActive = !item.active;
      const garmentName = item.name || item.prompt || partId;
      const chatInput = document.getElementById("chat-input");
      if (chatInput && typeof sendMessage === "function") {
        chatInput.value = nextActive
          ? `*สวม ${garmentName}*`
          : `*ถอด ${garmentName} ออก*`;
        await sendMessage({ manualWardrobe: true });
        return;
      }
      item.active = nextActive;

      // If clothing part is toggled ON, turn OFF naked
      if (CLOTHING_PART_KEYS.includes(partId)) {
        if (item.active) {
          if (currentWardrobe["naked"]) currentWardrobe["naked"].active = false;
        } else {
          // If all clothes are off, naked triggers automatically
          if (!isAnyClothingOn(currentWardrobe)) {
            currentWardrobe["naked"] = { active: true, prompt: "naked" };
          }
        }
      }

      // If unequipped/turned OFF, put the unequipped garment back to character's inventory bag
      if (!nextActive && activeCharacter) {
        try {
          const res = await fetch(`/api/characters/${encodeURIComponent(activeCharacter)}/inventory`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({
              action: "unequip",
              item: { slot: partId }
            })
          });
          const data = await res.json();
          if (data.ok && data.inventory) {
            currentInventory = data.inventory;
            renderInventoryList(currentInventory);
          }
        } catch (err) {
          console.warn("Failed to sync unequip to bag:", err);
        }
      }

      renderOutfits3x4Grid(currentWardrobe);
      await persistCurrentWardrobe();
    }

    function updateOutfitPrompt(partId, val) {
      if (!currentWardrobe[partId]) {
        currentWardrobe[partId] = { active: true, prompt: val };
      }
      currentWardrobe[partId].prompt = val;
    }

    // --- PER-SLOT WARDROBE CATALOG SYSTEM ---
    const cachedSlotItems = {};

    async function loadSlotItemsCatalog(slotKey) {
      if (cachedSlotItems[slotKey]) return cachedSlotItems[slotKey];
      try {
        const res = await fetch(`/api/wardrobe/items?slot=${encodeURIComponent(slotKey)}&limit=300`, {
          headers: { "Authorization": `Bearer ${token}` }
        });
        const data = await res.json();
        if (data.ok && Array.isArray(data.items)) {
          cachedSlotItems[slotKey] = data.items;
          return data.items;
        }
      } catch (err) {
        console.warn(`Failed to load wardrobe catalog for slot ${slotKey}:`, err);
      }
      return [];
    }

    async function onSelectSlotItem(partId, itemName, selectEl) {
      if (!itemName || !activeCharacter) return;

      // 1. Check if the item selected is from character's bag
      const bagItem = currentInventory.find(it => {
        const itemObj = (typeof it === "string") ? { name: it } : it;
        return itemObj.name === itemName;
      });

      if (bagItem) {
        // Equip directly from bag via inventory equip action
        await equipInventoryItemToWardrobe(itemName);
        return;
      }

      // 2. Otherwise equip from wardrobe slot catalog
      const items = cachedSlotItems[partId] || [];
      const found = items.find(it => it.name === itemName) || { name: itemName, prompt: itemName, category: partId };

      try {
        const res = await fetch(`/api/characters/${encodeURIComponent(activeCharacter)}/outfits/equip-item`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({
            slot: partId,
            item_name: found.name,
            item_prompt: found.prompt,
            category: found.category || partId
          })
        });
        const data = await res.json();
        if (data.ok && data.outfits) {
          currentWardrobe = data.outfits;
          renderOutfits3x4Grid(currentWardrobe);
          if (data.inventory) {
            currentInventory = data.inventory;
            renderInventoryList(currentInventory);
          }
          showNotice(`✨ สวมใส่ "${found.name}" ในช่อง [${partId}] เรียบร้อยแล้ว!`, "success");
        } else {
          throw new Error(data.error || "Failed to equip item");
        }
      } catch (err) {
        console.error("Error equipping slot item:", err);
        showNotice("สวมใส่ไอเทมไม่สำเร็จ: " + err.message, "error");
      }
    }

    // --- WARDROBE PRESET DROPDOWN SYSTEM ---
    let cachedWardrobePresets = [];

    async function loadWardrobePresetsCatalog() {
      if (cachedWardrobePresets.length > 0) return;
      try {
        const res = await fetch("/api/wardrobe/items?slot=preset&limit=300", {
          headers: { "Authorization": `Bearer ${token}` }
        });
        const data = await res.json();
        if (data.ok && Array.isArray(data.items)) {
          cachedWardrobePresets = data.items;
          populateWardrobePresetsDropdown();
        }
      } catch (err) {
        console.warn("Failed to load wardrobe presets catalog:", err);
      }
    }

    function populateWardrobePresetsDropdown() {
      const select = document.getElementById("wardrobe-preset-select");
      if (!select) return;
      select.innerHTML = '<option value="">-- เลือกชุดเซ็ตทั้งตัว (Full Preset) --</option>';

      // Group presets by category
      const groups = {};
      cachedWardrobePresets.forEach(item => {
        const rawCat = (item.category || "General").replace(/\\/g, " / ");
        if (!groups[rawCat]) groups[rawCat] = [];
        groups[rawCat].push(item);
      });

      Object.keys(groups).sort().forEach(cat => {
        const optgroup = document.createElement("optgroup");
        optgroup.label = `👗 ${cat}`;
        groups[cat].forEach(it => {
          const opt = document.createElement("option");
          opt.value = it.name;
          opt.textContent = it.name;
          opt.dataset.prompt = it.prompt;
          opt.dataset.category = it.category || "";
          optgroup.appendChild(opt);
        });
        select.appendChild(optgroup);
      });

      // Synchronize current preset selection
      if (currentWardrobe && currentWardrobe.current_preset) {
        select.value = currentWardrobe.current_preset;
      }
    }

    async function onSelectWardrobePreset(presetName) {
      if (!presetName || !activeCharacter) return;
      const found = cachedWardrobePresets.find(p => p.name === presetName);
      if (!found) return;

      try {
        const res = await fetch(`/api/characters/${encodeURIComponent(activeCharacter)}/outfits/preset`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({
            preset_name: found.name,
            preset_prompt: found.prompt,
            category: found.category || "preset"
          })
        });
        const data = await res.json();
        if (data.ok && data.outfits) {
          currentWardrobe = data.outfits;
          renderOutfits3x4Grid(currentWardrobe);
          showNotice(`👗 สวมใส่ชุด "${found.name}" เรียบร้อยแล้ว!`, "success");
        } else {
          throw new Error(data.error || "Failed to equip preset");
        }
      } catch (err) {
        console.error("Error equipping preset:", err);
        showNotice("สวมใส่ชุดไม่สำเร็จ: " + err.message, "error");
      }
    }

    // Helper to detect if an inventory item is wearable/clothing
    function isItemWearable(item) {
      if (!item) return false;
      const name = (item.name || "").toLowerCase();
      const desc = (item.desc || "").toLowerCase();
      const type = (item.type || "").toLowerCase();
      const combined = `${name} ${desc} ${type}`;
      const wearableKeywords = [
        "ชุดนอน", "เดรส", "dress", "gown", "ชุดว่ายน้ำ", "swimsuit", "bikini", "บิกินี่",
        "ชุดนักเรียน", "uniform", "kimono", "กิโมโน", "ยูกาตะ", "yukata", "cheongsam", "กี่เพ้า",
        "bunny suit", "bodysuit", "ชุดสูท", "suit", "pajamas", "costume", "เสื้อนอก", "เสื้อคลุม", "แจ็คเก็ต",
        "jacket", "coat", "blazer", "cardigan", "hoodie", "trench", "ยกทรง", "บรา", "bra",
        "กางเกงใน", "panties", "underwear", "เสื้อ", "shirt", "blouse", "sweater", "crop top",
        "กางเกง", "กระโปรง", "pants", "skirt", "jeans", "shorts", "รองเท้า", "shoes", "boots",
        "heels", "sneakers", "sandals", "ถุงเท้า", "ถุงน่อง", "socks", "stockings", "หมวก", "hat",
        "cap", "headband", "สร้อย", "สร้อยคอ", "necklace", "choker", "ปลอกคอ", "ถุงมือ", "gloves",
        "แหวน", "ring", "ริบบิ้น", "ribbon", "โบว์", "ต่างหู", "แว่น", "glasses"
      ];
      return wearableKeywords.some(k => combined.includes(k)) || ["clothing", "wearable", "accessory", "accessories", "apparel", "outfit"].includes(type);
    }

    // --- THEMED GIFTING APPROVAL POPUP ---
    let _giftApprovalResolve = null;
    let _currentGiftModalData = { maxQty: 1, currentQty: 1 };

    function openGiftApprovalModal({ itemName, itemDesc, itemIcon, rarity, maxQty = 1, charName }) {
      return new Promise(resolve => {
        _giftApprovalResolve = resolve;
        _currentGiftModalData = { maxQty: Math.max(1, maxQty), currentQty: 1 };

        const modal = document.getElementById("gift-approval-modal");
        const titleEl = document.getElementById("gift-modal-title");
        const iconBadge = document.getElementById("gift-modal-icon-badge");
        const nameEl = document.getElementById("gift-modal-item-name");
        const metaEl = document.getElementById("gift-modal-item-meta");
        const descEl = document.getElementById("gift-modal-item-desc");
        const charNameEl = document.getElementById("gift-modal-char-name");
        const qtyVal = document.getElementById("gift-modal-qty-val");
        const qtyCont = document.getElementById("gift-modal-qty-container");

        if (titleEl) titleEl.innerText = `มอบของขวัญให้ ${charName}`;
        if (iconBadge) iconBadge.innerText = itemIcon || "🎁";
        if (nameEl) nameEl.innerText = itemName;
        if (metaEl) metaEl.innerText = `${rarity || "Common"} · ของขวัญ / เครื่องแต่งกาย`;
        if (descEl) descEl.innerText = itemDesc || "ของขวัญชิ้นพิเศษที่จะช่วยสร้างความประทับใจและความสัมพันธ์ที่ดี";
        if (charNameEl) charNameEl.innerText = charName;
        if (qtyVal) qtyVal.innerText = "1";
        if (qtyCont) qtyCont.style.display = (_currentGiftModalData.maxQty > 1) ? "flex" : "none";

        if (modal) modal.style.display = "flex";
      });
    }

    function changeGiftModalQty(delta) {
      const next = Math.max(1, Math.min(_currentGiftModalData.maxQty, _currentGiftModalData.currentQty + delta));
      _currentGiftModalData.currentQty = next;
      const qtyVal = document.getElementById("gift-modal-qty-val");
      if (qtyVal) qtyVal.innerText = String(next);
    }

    function closeGiftApprovalModal(confirmed) {
      const modal = document.getElementById("gift-approval-modal");
      if (modal) modal.style.display = "none";
      if (_giftApprovalResolve) {
        const res = _giftApprovalResolve;
        _giftApprovalResolve = null;
        res(confirmed ? { confirmed: true, qty: _currentGiftModalData.currentQty } : null);
      }
    }

    function submitGiftApprovalModal() {
      closeGiftApprovalModal(true);
    }

    document.addEventListener("keydown", e => {
      if (e.key === "Escape" && document.getElementById("gift-approval-modal")?.style.display === "flex") {
        closeGiftApprovalModal(false);
      }
    });

    // Helper: Determine accurate icon matching wardrobe slot & item type
    function getWardrobeItemIcon(item) {
      if (!item) return "🎁";
      if (typeof item === "string") item = { name: item };
      if (item.icon && item.icon !== "👗" && item.icon !== "🎁") return item.icon;

      const slot = String(item.slot || "").toLowerCase();
      const name = String(item.name || "").toLowerCase();
      const prompt = String(item.prompt || "").toLowerCase();
      const combined = `${slot} ${name} ${prompt}`;

      if (slot === "preset" || combined.includes("set") || combined.includes("ชุดเซ็ต")) return "👑";
      if (slot === "head" || combined.includes("helm") || combined.includes("helmet") || combined.includes("หมวกเกราะ")) return "⛑️";
      if (combined.includes("hat") || combined.includes("cap") || combined.includes("beret") || combined.includes("beanie") || combined.includes("หมวก")) return "👒";
      if (slot === "head_acc" || combined.includes("ribbon") || combined.includes("hairband") || combined.includes("ริบบิ้น") || combined.includes("โบว์")) return "🎀";
      if (slot === "neck" || slot === "neck_acc" || combined.includes("necklace") || combined.includes("choker") || combined.includes("สร้อย") || combined.includes("ปลอกคอ")) return "📿";
      if (combined.includes("tie") || combined.includes("bowtie") || combined.includes("necktie") || combined.includes("เนคไท")) return "👔";
      if (slot === "hands" || slot === "hand_acc" || combined.includes("glove") || combined.includes("gauntlet") || combined.includes("ถุงมือ")) return "🧤";
      if (slot === "shoes" || combined.includes("boot") || combined.includes("boots") || combined.includes("greave") || combined.includes("เกราะขา")) return "🥾";
      if (combined.includes("shoe") || combined.includes("sneaker") || combined.includes("loafer") || combined.includes("heel") || combined.includes("flat") || combined.includes("รองเท้า")) return "👞";
      if (slot === "socks" || combined.includes("sock") || combined.includes("stocking") || combined.includes("tights") || combined.includes("legging") || combined.includes("ถุงเท้า") || combined.includes("ถุงน่อง")) return "🧦";
      if (slot === "top_inner" || slot === "bra" || combined.includes("bra") || combined.includes("bikini top") || combined.includes("บรา") || combined.includes("เสื้อใน")) return "👙";
      if (slot === "bottom_inner" || slot === "panties" || combined.includes("panties") || combined.includes("thong") || combined.includes("underwear") || combined.includes("กางเกงใน") || combined.includes("ชั้นใน")) return "🩲";
      if (slot === "outer" || slot === "outer_outfit" || combined.includes("jacket") || combined.includes("coat") || combined.includes("blazer") || combined.includes("cardigan") || combined.includes("hoodie") || combined.includes("เสื้อนอก") || combined.includes("เสื้อคลุม") || combined.includes("แจ็กเก็ต")) return "🧥";
      if (combined.includes("dress") || combined.includes("gown") || combined.includes("เดรส") || combined.includes("กระโปรงยาว")) return "👗";
      if (slot === "bottom" || combined.includes("skirt") || combined.includes("pants") || combined.includes("jeans") || combined.includes("shorts") || combined.includes("tasses") || combined.includes("กางเกง") || combined.includes("กระโปรง")) return "👖";
      if (slot === "top" || combined.includes("shirt") || combined.includes("blouse") || combined.includes("top") || combined.includes("t-shirt") || combined.includes("เสื้อ")) return "👚";
      if (slot === "leg_acc" || combined.includes("garter") || combined.includes("leg strap") || combined.includes("สายรัดขา")) return "🎗️";
      if (combined.includes("ring") || combined.includes("bracelet") || combined.includes("earring") || combined.includes("jewelry") || combined.includes("ต่างหู") || combined.includes("แหวน")) return "💍";
      if (item.type === "clothing" || item.type === "wearable") return "👗";
      return item.icon || "🎁";
    }

    // --- CHARACTER INVENTORY SYSTEM ---
    function renderInventoryList(items) {
      const container = document.getElementById("inventory-items-container");
      if (!container) return;
      container.innerHTML = "";

      if (!items || items.length === 0) {
        container.innerHTML = `<div class="inv-empty-state">ไม่มีไอเทมในกระเป๋า (กด "มอบของขวัญ/เพิ่มของ" เพื่อให้สิ่งของ)</div>`;
        return;
      }

      items.forEach(it => {
        const itemObj = (typeof it === "string") ? { name: it, qty: 1, desc: "" } : it;
        const name = itemObj.name || "Item";
        const qty = parseInt(itemObj.qty || 1, 10);
        const desc = itemObj.desc || "";
        const wearable = isItemWearable(itemObj);

        const card = document.createElement("div");
        card.className = "inv-item-card";

        const topRow = document.createElement("div");
        topRow.className = "inv-item-top";

        const nameSpan = document.createElement("div");
        nameSpan.className = "inv-item-name";
        const resolvedIcon = getWardrobeItemIcon(itemObj);
        nameSpan.innerHTML = `<span>${resolvedIcon} ${escapeHtml(name)}</span> <span class="inv-item-badge">x${qty}</span>`;

        topRow.appendChild(nameSpan);
        card.appendChild(topRow);

        if (desc) {
          const descSpan = document.createElement("div");
          descSpan.className = "inv-item-desc";
          descSpan.innerText = desc;
          card.appendChild(descSpan);
        }

        const actionsRow = document.createElement("div");
        actionsRow.className = "inv-item-actions";

        if (wearable) {
          const equipBtn = document.createElement("button");
          equipBtn.type = "button";
          equipBtn.className = "inv-btn-equip";
          equipBtn.innerText = "👗 สวมใส่";
          equipBtn.title = "สวมใส่ชุด/เครื่องประดับนี้เข้าช่อง Wardrobe ทันที";
          equipBtn.onclick = () => equipInventoryItemToWardrobe(name);
          actionsRow.appendChild(equipBtn);
        }

        const useBtn = document.createElement("button");
        useBtn.type = "button";
        useBtn.className = "inv-btn-use";
        useBtn.innerText = wearable ? "✨ ใช้งาน" : "✨ ใช้งาน";
        useBtn.title = "ให้ตัวละครใช้งานไอเทมนี้";
        useBtn.onclick = () => useInventoryItem(name);
        actionsRow.appendChild(useBtn);

        const delBtn = document.createElement("button");
        delBtn.type = "button";
        delBtn.className = "inv-btn-del";
        delBtn.innerText = "🗑 นำออก";
        delBtn.title = "ทิ้งหรือนำไอเทมออกจากกระเป๋า";
        delBtn.onclick = () => removeInventoryItem(name);
        actionsRow.appendChild(delBtn);

        card.appendChild(actionsRow);
        container.appendChild(card);
      });
    }

    async function equipInventoryItemToWardrobe(name) {
      if (!activeCharacter) return;
      if (!await openConfirmDialog(`ต้องการให้ ${activeCharacter} สวมใส่ "${name}" เข้าสู่ Wardrobe หรือไม่?`, "👗 ยืนยันการสวมใส่ชุด", "สวมใส่", "ยกเลิก")) return;

      try {
        const res = await fetch(`/api/characters/${encodeURIComponent(activeCharacter)}/inventory`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({
            action: "equip",
            item: { name: name, qty: 1 }
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "ไม่สามารถสวมใส่ไอเทมได้");

        currentInventory = data.inventory || [];
        renderInventoryList(currentInventory);

        if (data.outfits) {
          currentWardrobe = data.outfits;
          renderOutfits3x4Grid(currentWardrobe);
        }
        showNotice(data.message || `สวมใส่ "${name}" สำเร็จ!`, "success");

        // Suggest in chat input if empty
        const chatInput = document.getElementById("chat-input");
        if (chatInput && !chatInput.value.trim()) {
          chatInput.value = `*หยิบ ${name} ออกมาสวมใส่เข้ากับตัว*`;
          chatInput.focus();
        }
      } catch (err) {
        showNotice(err.message, "error");
      }
    }

    async function promptGiveGiftToCharacter() {
      if (!activeCharacter) {
        showNotice("กรุณาPlease select a character first", "error");
        return;
      }
      const itemName = prompt("ระบุชื่อสิ่งของ / ของขวัญที่ต้องการมอบให้ " + activeCharacter + ":");
      if (!itemName || !itemName.trim()) return;

      const itemDesc = prompt("คำอธิบายหรือผลของไอเทม (สามารถเว้นว่างได้):", "") || "";
      const itemQtyStr = prompt("จำนวนชิ้น:", "1");
      const itemQty = Math.max(1, parseInt(itemQtyStr, 10) || 1);

      try {
        const res = await fetch(`/api/characters/${encodeURIComponent(activeCharacter)}/inventory`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({
            action: "add",
            item: {
              name: itemName.trim(),
              desc: itemDesc.trim(),
              qty: itemQty
            }
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "ไม่สามารถเพิ่มไอเทมได้");
        currentInventory = data.inventory || [];
        renderInventoryList(currentInventory);
        showNotice(`มอบ "${itemName.trim()}" ให้ ${activeCharacter} เรียบร้อยแล้ว!`);
      } catch (err) {
        showNotice(err.message, "error");
      }
    }

    async function useInventoryItem(name) {
      if (!activeCharacter) return;
      if (!await openConfirmDialog(`ต้องการให้ ${activeCharacter} นำ "${name}" ออกมาใช้งานใช่หรือไม่?`, "✨ ใช้งานไอเทม", "ใช้งาน", "ยกเลิก")) return;

      try {
        const res = await fetch(`/api/characters/${encodeURIComponent(activeCharacter)}/inventory`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({
            action: "use",
            item: { name: name, qty: 1 }
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "ไม่สามารถใช้งานไอเทมได้");
        currentInventory = data.inventory || [];
        renderInventoryList(currentInventory);
        if (data.outfits) {
          currentWardrobe = data.outfits;
          renderOutfits3x4Grid(currentWardrobe);
        }
        showNotice(data.message || `${activeCharacter} ใช้งาน "${name}" แล้ว`, "success");

        // Suggest usage in chat input if empty
        const chatInput = document.getElementById("chat-input");
        if (chatInput && !chatInput.value.trim()) {
          chatInput.value = `*หยิบ ${name} ออกมาใช้งาน*`;
          chatInput.focus();
        }
      } catch (err) {
        showNotice(err.message, "error");
      }
    }

    async function removeInventoryItem(name) {
      if (!activeCharacter) return;
      if (!confirm(`ยืนยันการนำ "${name}" ออกจากกระเป๋าของ ${activeCharacter} หรือไม่?`)) return;

      try {
        const res = await fetch(`/api/characters/${encodeURIComponent(activeCharacter)}/inventory`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({
            action: "remove",
            item: { name: name, qty: 1 }
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "ไม่สามารถลบไอเทมได้");
        currentInventory = data.inventory || [];
        renderInventoryList(currentInventory);
        showNotice(`นำ "${name}" ออกจากกระเป๋าแล้ว`);
      } catch (err) {
        showNotice(err.message, "error");
      }
    }

    // --- PLAYER REWARDS & RPG SYSTEM LOGIC ---
    let currentPlayerRewards = null;

    function updatePlayerRewardsUI(rewardsData) {
      if (!rewardsData) return;
      currentPlayerRewards = rewardsData;

      // Update Top Bar Badges
      const topLv = document.getElementById("top-reward-lv");
      if (topLv) topLv.innerText = rewardsData.level || 1;
      const topCoins = document.getElementById("top-reward-coins");
      if (topCoins) topCoins.innerText = rewardsData.coins || 0;

      // Update Modal Header
      const rpgLv = document.getElementById("rpg-level-val");
      if (rpgLv) rpgLv.innerText = rewardsData.level || 1;
      const rpgExp = document.getElementById("rpg-exp-val");
      if (rpgExp) rpgExp.innerText = rewardsData.exp || 0;
      const rpgNext = document.getElementById("rpg-exp-next");
      if (rpgNext) rpgNext.innerText = rewardsData.next_exp || 100;

      const pct = Math.min(100, Math.max(0, Math.round(((rewardsData.exp || 0) / (rewardsData.next_exp || 100)) * 100)));
      const expBar = document.getElementById("rpg-exp-bar");
      if (expBar) expBar.style.width = `${pct}%`;

      const rpgCoins = document.getElementById("rpg-coins-val");
      if (rpgCoins) rpgCoins.innerText = rewardsData.coins || 0;
      document.querySelectorAll(".shop-coins-val, .gacha-coins-val").forEach(el => {
        el.innerText = rewardsData.coins || 0;
      });
      const rpgStatPts = document.getElementById("rpg-stat-pts-val");
      if (rpgStatPts) rpgStatPts.innerText = rewardsData.stat_points || 0;
      const rpgSkillPts = document.getElementById("rpg-skill-pts-val");
      if (rpgSkillPts) rpgSkillPts.innerText = rewardsData.skill_points || 0;

      const rpgInvCount = document.getElementById("rpg-inv-count");
      if (rpgInvCount) rpgInvCount.innerText = (rewardsData.inventory || []).length;

      // Update Sidebar Player Card Widget (Red Area)
      const sideName = document.getElementById("sidebar-player-name");
      if (sideName) sideName.innerText = currentDisplayName || currentUser || "Player";
      const sideLv = document.getElementById("sidebar-player-lv-badge");
      if (sideLv) sideLv.innerText = `LV.${rewardsData.level || 1}`;
      const sideCoins = document.getElementById("sidebar-player-coins");
      if (sideCoins) sideCoins.innerText = rewardsData.coins || 0;
      const sideExpFill = document.getElementById("sidebar-player-exp-fill");
      if (sideExpFill) sideExpFill.style.width = `${pct}%`;
      const sideExpVal = document.getElementById("sidebar-player-exp-val");
      if (sideExpVal) sideExpVal.innerText = rewardsData.exp || 0;
      const sideExpNext = document.getElementById("sidebar-player-exp-next");
      if (sideExpNext) sideExpNext.innerText = rewardsData.next_exp || 100;
      const sideAvatar = document.getElementById("sidebar-player-avatar");
      if (sideAvatar && currentUser) {
        sideAvatar.src = `https://api.dicebear.com/7.x/bottts/svg?seed=${encodeURIComponent(currentUser)}`;
      }

      // Render Tabs Content
      renderRpgStats(rewardsData);
      renderRpgSkills(rewardsData);
      renderPlayerInventory(rewardsData.inventory || []);
    }

    function renderRpgStats(data) {
      const container = document.getElementById("rpg-stats-container");
      if (!container) return;
      container.innerHTML = "";

      const statNames = {
        str: { label: "Strength (พละกำลัง)", icon: "💪" },
        agi: { label: "Agility (ความคล่องแคล่ว)", icon: "⚡" },
        int: { label: "Intelligence (สติปัญญา)", icon: "🧠" },
        luk: { label: "Luck (โชคชะตา & ดรอปเรต)", icon: "🍀" },
        cha: { label: "Charisma (เสน่ห์วาจา & EXP)", icon: "💖" }
      };

      const statPts = data.stat_points || 0;
      const stats = data.stats || {};

      Object.keys(statNames).forEach(k => {
        const info = statNames[k];
        const val = stats[k] || 10;
        const box = document.createElement("div");
        box.className = "rpg-stat-box";

        const left = document.createElement("div");
        left.innerHTML = `<span class="rpg-stat-label">${info.icon} ${info.label}</span>`;

        const right = document.createElement("div");
        right.style.display = "flex";
        right.style.alignItems = "center";
        right.innerHTML = `<span class="rpg-stat-val">${val}</span>`;

        if (statPts > 0) {
          const btn = document.createElement("button");
          btn.className = "rpg-add-btn";
          btn.innerText = "+1";
          btn.title = `เพิ่มแต้ม ${info.label}`;
          btn.onclick = () => allocateStat(k);
          right.appendChild(btn);
        }

        box.appendChild(left);
        box.appendChild(right);
        container.appendChild(box);
      });
    }

    function renderRpgSkills(data) {
      const container = document.getElementById("rpg-skills-container");
      if (!container) return;
      container.innerHTML = "";

      const skillPts = data.skill_points || 0;
      const skills = data.skills || [];

      skills.forEach(sk => {
        const card = document.createElement("div");
        card.className = "rpg-skill-card";

        const info = document.createElement("div");
        info.innerHTML = `
          <div style="font-size:12px; font-weight:700; color:#f1f5f9;">${escapeHtml(sk.name)} <span style="color:#f472b6; font-size:11px;">[Lv.${sk.level}/${sk.max_level}]</span></div>
          <div style="font-size:11px; color:var(--text-muted); margin-top:2px;">${escapeHtml(sk.desc)}</div>
        `;

        const right = document.createElement("div");
        if (sk.level >= sk.max_level) {
          right.innerHTML = `<span style="font-size:11px; color:#10b981; font-weight:700;">MAX</span>`;
        } else if (skillPts > 0) {
          const btn = document.createElement("button");
          btn.className = "rpg-add-btn";
          btn.innerText = "อัปเกรด (1 pt)";
          btn.onclick = () => upgradeSkill(sk.id);
          right.appendChild(btn);
        } else {
          right.innerHTML = `<span style="font-size:11px; color:var(--text-muted);">ต้องการ 1 pt</span>`;
        }

        card.appendChild(info);
        card.appendChild(right);
        container.appendChild(card);
      });
    }

    function renderPlayerInventory(items) {
      const container = document.getElementById("rpg-player-inventory-container");
      if (!container) return;
      container.innerHTML = "";

      if (!items || items.length === 0) {
        container.innerHTML = `<div class="inv-empty-state">ไม่มีไอเทมในกระเป๋าของคุณ (ซื้อของจากร้านค้า หรือสุ่มกาชาได้)</div>`;
        return;
      }

      items.forEach(it => {
        const name = it.name || "Item";
        const qty = parseInt(it.qty || 1, 10);
        const desc = it.desc || "";
        const icon = getWardrobeItemIcon(it);
        const rarity = it.rarity || "Common";

        const card = document.createElement("div");
        card.className = `inv-item-card ${rarity}`;

        const top = document.createElement("div");
        top.className = "inv-item-top";
        top.innerHTML = `
          <div class="inv-item-name"><span>${icon} ${escapeHtml(name)}</span> <span class="inv-item-badge">x${qty}</span></div>
          <span style="font-size:10px; color:#c4b5fd; font-weight:600;">${rarity}</span>
        `;
        card.appendChild(top);

        if (desc) {
          const d = document.createElement("div");
          d.className = "inv-item-desc";
          d.innerText = desc;
          card.appendChild(d);
        }

        const actions = document.createElement("div");
        actions.className = "inv-item-actions";

        const giveBtn = document.createElement("button");
        giveBtn.type = "button";
        giveBtn.className = "inv-btn-use";
        giveBtn.innerText = activeCharacter ? `🎁 มอบให้ ${activeCharacter}` : "🎁 มอบให้ตัวละคร";
        giveBtn.onclick = () => giveGiftFromPlayerBag(name);
        actions.appendChild(giveBtn);

        if (it.type === "h_item") {
          const useBtn = document.createElement("button");
          useBtn.type = "button";
          useBtn.className = "inv-btn-use";
          useBtn.innerText = activeCharacter ? `✨ ใช้กับ ${activeCharacter}` : "✨ ใช้งาน";
          useBtn.title = "ใช้ H-item จาก Player Bag โดยตรงกับตัวละคร โดยไม่มอบหรือย้าย item";
          useBtn.onclick = () => useHItemFromPlayerBag(name);
          actions.appendChild(useBtn);
        }

        card.appendChild(actions);
        container.appendChild(card);
      });
    }

    let currentShopCategory = "general";
    let currentShopSlot = "";
    let currentShopOffset = 0;

    function setShopCategory(category) {
      currentShopCategory = category;
      currentShopOffset = 0;
      const isWardrobe = (currentShopCategory === "wardrobe");
      const subcats = document.getElementById("rpg-shop-subcategories");
      const search = document.getElementById("rpg-shop-search");
      if (subcats) subcats.style.display = isWardrobe ? "flex" : "none";
      if (search) {
        search.style.display = isWardrobe ? "block" : "none";
        search.placeholder = (currentShopSlot === "preset") ? "ค้นหาชุดเซ็ต (เช่น high school, blazer, dress)..." : "ค้นหาชุด...";
      }
      document.getElementById("rpg-shop-general-btn")?.classList.toggle("active", currentShopCategory === "general");
      document.getElementById("rpg-shop-wardrobe-btn")?.classList.toggle("active", isWardrobe);
      document.getElementById("rpg-shop-h-items-btn")?.classList.toggle("active", currentShopCategory === "h_items");
      updateShopSubcategoryButtons();
      loadShopCatalog(0);
    }

    function setShopSlotFilter(slot) {
      currentShopSlot = slot;
      currentShopOffset = 0;
      updateShopSubcategoryButtons();
      const search = document.getElementById("rpg-shop-search");
      if (search) {
        search.placeholder = (slot === "preset") ? "ค้นหาชุดเซ็ต (เช่น high school, blazer, dress)..." : `ค้นหา ${slot || 'ชุด'}...`;
      }
      loadShopCatalog(0);
    }

    function updateShopSubcategoryButtons() {
      document.querySelectorAll("[data-shop-slot]").forEach(btn => {
        const slot = btn.dataset.shopSlot;
        const isActive = (slot === currentShopSlot);
        btn.style.outline = isActive ? "2px solid #f472b6" : "none";
        btn.style.boxShadow = isActive ? "0 0 10px rgba(244,114,182,0.4)" : "none";
      });
    }

    async function loadShopCatalog(offset = currentShopOffset) {
      try {
        const search = document.getElementById("rpg-shop-search")?.value || "";
        const effectiveCategory = currentShopCategory;
        const effectiveSlot = (currentShopCategory === "wardrobe") ? currentShopSlot : "";
        const params = new URLSearchParams({category: effectiveCategory, limit: "36", offset: String(Math.max(0, offset))});
        if (effectiveSlot) params.set("slot", effectiveSlot);
        if (currentShopCategory === "wardrobe" && search.trim()) params.set("q", search.trim());
        const res = await fetch(`/api/rewards/shop?${params.toString()}`, {
          headers: { "Authorization": `Bearer ${token}` }
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "โหลดร้านค้าไม่สำเร็จ");
        currentShopOffset = Number(data.offset || 0);
        const badge = document.getElementById("rpg-shop-discount-badge");
        if (badge) {
          badge.innerText = data.discount_pct > 0 ? `✨ ส่วนลด Bargaining: -${data.discount_pct}%` : "";
        }

        const container = document.getElementById("rpg-shop-items-container");
        if (!container) return;
        container.innerHTML = "";

        const catalog = data.catalog || [];
        catalog.forEach(it => {
          const card = document.createElement("div");
          card.className = "rpg-shop-card";

          const discountMult = Math.max(0.6, 1.0 - ((data.discount_pct || 0) / 100));
          const finalPrice = Math.max(1, Math.round(it.price * discountMult));
          const isPresetItem = (it.slot === "preset" || currentShopCategory === "sets" || currentShopSlot === "preset");

          let itemsListHtml = '';
          if (isPresetItem && it.prompt) {
            const rawParts = it.prompt.split(',').map(p => p.trim()).filter(Boolean);
            if (rawParts.length > 0) {
              const tagsHtml = rawParts.map(part => {
                let icon = '👗';
                const pLow = part.toLowerCase();
                if (pLow.includes('helm') || pLow.includes('helmet') || pLow.includes('headgear')) icon = '⛑️';
                else if (pLow.includes('gauntlet') || pLow.includes('glove') || pLow.includes('armguard')) icon = '🧤';
                else if (pLow.includes('greave') || pLow.includes('sabaton')) icon = '🛡️';
                else if (pLow.includes('tasses') || pLow.includes('fauld') || pLow.includes('cuisse')) icon = '🛡️';
                else if (pLow.includes('armor') || pLow.includes('cuirass') || pLow.includes('breastplate') || pLow.includes('chestplate')) icon = '🛡️';
                else if (pLow.includes('blazer') || pLow.includes('jacket') || pLow.includes('coat') || pLow.includes('cardigan') || pLow.includes('vest')) icon = '🧥';
                else if (pLow.includes('shirt') || pLow.includes('blouse') || pLow.includes('top')) icon = '👚';
                else if (pLow.includes('skirt') || pLow.includes('pants') || pLow.includes('shorts') || pLow.includes('jeans')) icon = '👖';
                else if (pLow.includes('sock') || pLow.includes('stocking') || pLow.includes('tights')) icon = '🧦';
                else if (pLow.includes('shoe') || pLow.includes('loafer') || pLow.includes('sneaker') || pLow.includes('boot') || pLow.includes('pump') || pLow.includes('heel') || pLow.includes('flat')) icon = '👞';
                else if (pLow.includes('tie') || pLow.includes('ribbon') || pLow.includes('bow')) icon = '🎀';
                return `<span style="display:inline-flex; align-items:center; gap:4px; padding:2px 7px; background:rgba(124,58,237,0.18); border:1px solid rgba(192,132,252,0.3); border-radius:6px; font-size:10px; color:#e9d5ff;">${icon} ${escapeHtml(part)}</span>`;
              }).join('');

              itemsListHtml = `
                <div style="margin-top:6px; padding:6px 8px; background:rgba(0,0,0,0.35); border-radius:8px; border:1px dashed rgba(216,180,254,0.3);">
                  <div style="font-size:10px; font-weight:700; color:#f0abfc; margin-bottom:4px; text-transform:uppercase; letter-spacing:0.04em;">🎁 ชิ้นส่วนในเซ็ต (${rawParts.length} ชิ้น):</div>
                  <div style="display:flex; flex-wrap:wrap; gap:4px;">${tagsHtml}</div>
                </div>
              `;
            }
          }

          let colorSelectorHtml = '';
          const isWearablePiece = (it.type === 'clothing' || it.type === 'wearable' || currentShopCategory === 'wardrobe') && !isPresetItem;
          if (isWearablePiece) {
            const safeSelectId = 'shop-color-' + it.id.replace(/[^a-zA-Z0-9_-]/g, '_');
            const colorOptions = [
              { val: '', label: '🎨 สีเริ่มต้น' },
              { val: 'black', label: '🖤 Black' },
              { val: 'white', label: '🤍 White' },
              { val: 'red', label: '❤️ Red' },
              { val: 'crimson', label: '🍷 Crimson' },
              { val: 'blue', label: '💙 Blue' },
              { val: 'navy', label: '⚓ Navy' },
              { val: 'cyan', label: '💎 Cyan' },
              { val: 'teal', label: '🩵 Teal' },
              { val: 'green', label: '💚 Green' },
              { val: 'yellow', label: '💛 Yellow' },
              { val: 'pink', label: '💖 Pink' },
              { val: 'purple', label: '💜 Purple' },
              { val: 'violet', label: '🔮 Violet' },
              { val: 'lavender', label: '🪻 Lavender' },
              { val: 'orange', label: '🧡 Orange' },
              { val: 'brown', label: '🤎 Brown' },
              { val: 'beige', label: '🌾 Beige' },
              { val: 'gray', label: '🩶 Gray' },
              { val: 'silver', label: '✨ Silver' },
              { val: 'gold', label: '👑 Gold' }
            ];
            const optHtml = colorOptions.map(c => `<option value="${c.val}">${c.label}</option>`).join('');
            colorSelectorHtml = `
              <div style="margin-top:6px; display:flex; align-items:center; gap:6px;">
                <label style="font-size:11px; color:#cbd5e1; white-space:nowrap;">🎨 สี:</label>
                <select id="${safeSelectId}" style="flex:1; padding:3px 6px; font-size:11px; border-radius:6px; background:rgba(15,23,42,0.85); color:#f8fafc; border:1px solid rgba(255,255,255,0.18);">
                  ${optHtml}
                </select>
              </div>
            `;
          }

          const safeItemId = decodeURIComponent(encodeURIComponent(it.id));
          const safeSelectIdParam = isWearablePiece ? `'shop-color-' + '${it.id.replace(/[^a-zA-Z0-9_-]/g, '_')}'` : 'null';

          const cardIcon = isPresetItem ? '👑' : getWardrobeItemIcon(it);
          card.innerHTML = `
            <div style="font-size: 24px; text-align: center;">${cardIcon}</div>
            <div style="font-size: 13px; font-weight: 700; color: #fff; text-align:center;">${escapeHtml(it.name)}</div>
            <div style="font-size: 11px; color: var(--text-muted); line-height: 1.35; flex: 1;">${escapeHtml(it.desc || '')}</div>
            ${itemsListHtml}
            ${colorSelectorHtml}
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px;">
              <span style="font-size: 12px; font-weight: 700; color: #38bdf8;">🪙 ${finalPrice} Coins</span>
              <button class="btn" style="padding: 4px 10px; font-size: 11px; ${isPresetItem ? 'background:linear-gradient(135deg,#ec4899,#7c3aed); border-color:#f0abfc;' : ''}" onclick="handleBuyShopItem(decodeURIComponent('${encodeURIComponent(it.id)}'), 1, ${safeSelectIdParam})">${isPresetItem ? '✨ ซื้อทั้งเซ็ต' : 'ซื้อ'}</button>
            </div>
          `;
          container.appendChild(card);
        });
        if (!catalog.length) container.innerHTML = `<div style="color:var(--text-muted); padding:12px;">ไม่พบรายการในหมวดนี้</div>`;

        const pager = document.getElementById("rpg-shop-pagination");
        if (pager) {
          const total = Number(data.total || catalog.length), pageSize = Number(data.limit || 36);
          const page = Math.floor(currentShopOffset / pageSize) + 1, pages = Math.max(1, Math.ceil(total / pageSize));
          pager.style.display = (currentShopCategory === "wardrobe" || currentShopCategory === "sets") && total > pageSize ? "flex" : "none";
          pager.innerHTML = `<button class="btn" style="padding:4px 10px; font-size:11px;" ${currentShopOffset ? "" : "disabled"} onclick="loadShopCatalog(${Math.max(0, currentShopOffset - pageSize)})">← ก่อนหน้า</button><span>${page} / ${pages} · ${total} รายการ</span><button class="btn" style="padding:4px 10px; font-size:11px;" ${currentShopOffset + pageSize < total ? "" : "disabled"} onclick="loadShopCatalog(${currentShopOffset + pageSize})">ถัดไป →</button>`;
        }
      } catch (e) {
        console.error("loadShopCatalog error:", e);
      }
    }

    // --- 1. USER STATUS & ATTRIBUTES MODAL ---
    async function openUserStatusModal(defaultTab = 'stats') {
      const modal = document.getElementById("user-status-modal");
      if (modal) modal.style.display = "flex";
      switchUserStatusTab(defaultTab);
      await fetchPlayerRewardsProfile();
    }
    function closeUserStatusModal() {
      const modal = document.getElementById("user-status-modal");
      if (modal) modal.style.display = "none";
    }
    function switchUserStatusTab(tabId) {
      ["stats", "inv"].forEach(t => {
        const btn = document.getElementById(`user-status-tab-btn-${t}`);
        const content = document.getElementById(`user-status-tab-content-${t}`);
        if (btn) btn.classList.toggle("active", t === tabId);
        if (content) content.style.display = (t === tabId) ? "flex" : "none";
      });
    }

    // --- 2. STORE (ITEM & WARDROBE SHOP) MODAL ---
    async function openItemShopModal(category = 'general') {
      const modal = document.getElementById("item-shop-modal");
      if (modal) modal.style.display = "flex";
      setShopCategory(category);
      await fetchPlayerRewardsProfile();
    }
    function closeItemShopModal() {
      const modal = document.getElementById("item-shop-modal");
      if (modal) modal.style.display = "none";
    }

    // --- 3. GACHA BOX MODAL ---
    async function openGachaModal() {
      const modal = document.getElementById("gacha-modal");
      if (modal) modal.style.display = "flex";
      await fetchPlayerRewardsProfile();
    }
    function closeGachaModal() {
      const modal = document.getElementById("gacha-modal");
      if (modal) modal.style.display = "none";
    }

    // Backward compatibility helper
    async function openPlayerRewardsModal() {
      openUserStatusModal('stats');
    }
    function closePlayerRewardsModal() {
      closeUserStatusModal();
      closeItemShopModal();
      closeGachaModal();
    }
    function switchRpgTab(tabId) {
      if (tabId === 'stats' || tabId === 'inv') {
        openUserStatusModal(tabId);
      } else if (tabId === 'shop') {
        openItemShopModal('general');
      } else if (tabId === 'gacha') {
        openGachaModal();
      }
    }

    async function fetchPlayerRewardsProfile() {
      try {
        const res = await fetch("/api/rewards/profile", {
          headers: { "Authorization": `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          updatePlayerRewardsUI(data);
        }
      } catch (e) {
        console.error("Failed to fetch player rewards profile:", e);
      }
    }

    async function allocateStat(statName) {
      try {
        const res = await fetch("/api/rewards/stat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({ stat_name: statName, amount: 1 })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "ไม่สามารถอัปเกรดค่าพลังได้");
        updatePlayerRewardsUI(data.profile);
      } catch (e) {
        showNotice(e.message, "error");
      }
    }

    async function upgradeSkill(skillId) {
      try {
        const res = await fetch("/api/rewards/skill", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({ skill_id: skillId })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "ไม่สามารถอัปเกรดสกิลได้");
        updatePlayerRewardsUI(data.profile);
      } catch (e) {
        showNotice(e.message, "error");
      }
    }

    function handleBuyShopItem(itemId, qty = 1, selectId = null) {
      let selectedColor = null;
      if (selectId) {
        const sel = document.getElementById(selectId);
        if (sel && sel.value) {
          selectedColor = sel.value;
        }
      }
      buyShopItem(itemId, qty, selectedColor);
    }

    async function buyShopItem(itemId, qty = 1, color = null) {
      try {
        const payload = { item_id: itemId, qty: qty };
        if (color) payload.color = color;
        const res = await fetch("/api/rewards/buy", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "ไม่สามารถซื้อไอเทมได้");
        updatePlayerRewardsUI(data.profile);
        showNotice(data.message);
      } catch (e) {
        showNotice(e.message, "error");
      }
    }

    async function executeGachaPull(pullCount = 1, poolType = "gift") {
      try {
        const res = await fetch("/api/rewards/gacha", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({ pull_count: pullCount, pool_type: poolType })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "การสุ่มไม่สำเร็จ");
        updatePlayerRewardsUI(data.profile);

        const resultsSec = document.getElementById("gacha-results-section");
        const cardsCont = document.getElementById("gacha-result-cards-container");
        if (resultsSec && cardsCont) {
          resultsSec.style.display = "flex";
          cardsCont.innerHTML = "";
          (data.items || []).forEach(it => {
            const c = document.createElement("div");
            c.className = `gacha-item-card ${it.rarity}`;
            c.innerHTML = `
              <div style="font-size:20px;">${it.icon || '🎁'}</div>
              <div style="font-weight:700; color:#fff; margin-top:2px;">${escapeHtml(it.name)}</div>
              <div style="font-size:10px; color:${it.rarity === 'SSR' ? '#f59e0b' : it.rarity === 'Rare' ? '#c084fc' : '#94a3b8'}; font-weight:700;">${it.rarity}</div>
            `;
            cardsCont.appendChild(c);
          });
        }
        showNotice(`สุ่ม ${data.pool_label || "Gacha"} สำเร็จ! ได้รับไอเทม ${data.items.length} ชิ้น เข้ากระเป๋าแล้ว`);
      } catch (e) {
        showNotice(e.message, "error");
      }
    }

    async function giveGiftFromPlayerBag(itemName) {
      if (!activeCharacter) {
        showNotice("กรุณาเลือกตัวละครที่ต้องการมอบให้ก่อน", "error");
        return;
      }

      // Find item details from player inventory
      const inv = (currentPlayerRewards && currentPlayerRewards.inventory) ? currentPlayerRewards.inventory : [];
      const item = inv.find(i => i.name === itemName) || { name: itemName, qty: 1 };
      const itemIcon = getWardrobeItemIcon(item);

      // Open UI Theme Skinned Center Modal for approval
      const approval = await openGiftApprovalModal({
        itemName: item.name,
        itemDesc: item.desc || "",
        itemIcon: itemIcon,
        rarity: item.rarity || "Common",
        maxQty: parseInt(item.qty || 1, 10),
        charName: activeCharacter
      });

      if (!approval || !approval.confirmed) return;
      const sendQty = approval.qty || 1;

      try {
        const res = await fetch("/api/rewards/give_gift", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({
            character_name: activeCharacter,
            item_name: itemName,
            qty: sendQty
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "ไม่สามารถมอบของขวัญได้");

        updatePlayerRewardsUI(data.player_profile);
        currentInventory = data.character_inventory || [];
        renderInventoryList(currentInventory);
        showNotice(data.message, "success");

        // If history returned with character reaction, update chat history and character state
        if (data.history && Array.isArray(data.history)) {
          renderChatHistory(data.history, true);
        }
        if (data.state && typeof applyResponseState === "function") {
          applyResponseState(data.state);
        }
      } catch (e) {
        showNotice(e.message, "error");
      }
    }

    async function useHItemFromPlayerBag(itemName) {
      if (!activeCharacter) {
        showNotice("กรุณาเลือกตัวละครก่อนใช้งาน H-item", "error");
        return;
      }
      const inv = (currentPlayerRewards && currentPlayerRewards.inventory) ? currentPlayerRewards.inventory : [];
      const item = inv.find(i => i.name === itemName);
      if (!item || item.type !== "h_item") {
        showNotice("ไม่พบ H-item นี้ใน Player Bag", "error");
        return;
      }
      if (!await openConfirmDialog(
        `ต้องการใช้ "${itemName}" จาก Player Bag กับ ${activeCharacter} หรือไม่?\nitem จะไม่ถูกมอบ ย้าย หรือหายไป`,
        "✨ ใช้ H-item", "ใช้งาน", "ยกเลิก"
      )) return;

      try {
        const useRes = await fetch("/api/rewards/use_h_item", {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
          body: JSON.stringify({ character_name: activeCharacter, item_name: itemName })
        });
        const used = await useRes.json();
        if (!useRes.ok) throw new Error(used.detail || "ไม่สามารถใช้ H-item ได้");

        updatePlayerRewardsUI(used.player_profile);
        if (typeof loadCharacterState === "function") loadCharacterState(activeCharacter);
        showNotice(used.message || `${activeCharacter} ใช้งาน "${itemName}" แล้ว`, "success");
      } catch (err) {
        showNotice(err.message, "error");
      }
    }

    // --- RIGHT PANE TAB 2: CHARACTER GALLERY ---
    async function loadCharacterGallery(charName, sprites) {
      try {
        const res = await fetch(`/api/characters/${encodeURIComponent(charName)}/gallery`, {
          headers: { "Authorization": `Bearer ${token}` }
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Could not load gallery");
        if (activeCharacter !== charName) return;
        renderGalleryTiles(charName, sprites, data.items || []);
      } catch (err) {
        if (activeCharacter !== charName) return;
        console.error("loadCharacterGallery error:", err);
        renderGalleryTiles(charName, sprites, []);
      }
    }

    function renderGalleryTiles(charName, sprites, generatedItems = []) {
      const container = document.getElementById("gallery-tiles-container");
      container.innerHTML = "";
      const allItems = Array.isArray(generatedItems) ? generatedItems : [];
      document.getElementById("pane-gallery-count").innerText = (sprites?.length || 0) + allItems.length;

      const addTitle = title => {
        const heading = document.createElement("div");
        heading.className = "gallery-section-title";
        heading.textContent = title;
        container.appendChild(heading);
      };
      const addImage = (src, label) => {
        const tile = document.createElement("div");
        tile.className = "gallery-tile-item";
        tile.title = label;
        tile.innerHTML = `<img src="${src}" alt="${escapeHtml(label)}">`;
        tile.onclick = () => openImageLightbox(src);
        container.appendChild(tile);
      };

      const profile = allItems.filter(item => item.kind === "profile");
      const generated = allItems.filter(item => item.kind === "generated");
      if (profile.length) {
        addTitle("Character Profile");
        profile.forEach(item => addImage(item.url, "Character profile image"));
      }
      if (generated.length) {
        addTitle(`Generated Images · ${generated.length}`);
        generated.forEach((item, index) => addImage(item.url, `Generated image ${generated.length - index}`));
      }

      if (sprites && sprites.length) {
        addTitle(`Character Card Sprites · ${sprites.length}`);
        sprites.forEach(s => {
        const spriteSrc = `/api/characters/${encodeURIComponent(charName)}/sprites/${encodeURIComponent(s)}`;
          addImage(spriteSrc, s);
        });
      }

      if (!container.children.length) {
        container.innerHTML = `<span style="font-size:12px; color:var(--text-muted); grid-column: span 3;">ยังไม่มีรูปภาพสำหรับตัวละครนี้</span>`;
      }
    }

    // --- ROLEPLAY FORMATTER ---
    function renderStateBlocksCollapsible(blocks) {
      if (!blocks || !blocks.length) return "";
      const blockHtmls = blocks.map(b => {
        let labelIcon = "📊";
        if (/status/i.test(b.label)) labelIcon = "🧘";
        else if (/situation|scenario/i.test(b.label)) labelIcon = "📍";
        else if (/memor/i.test(b.label)) labelIcon = "🧠";
        else if (/emotion/i.test(b.label)) labelIcon = "🎭";
        else if (/wardrobe/i.test(b.label)) labelIcon = "👗";

        let content = b.content.replace(/\u200b/g, '').trim();
        // If it's JSON emotion block, format nicely
        if (/emotion/i.test(b.label) && content.startsWith('{') && content.endsWith('}')) {
          try {
            const parsed = JSON.parse(content);
            const items = Object.entries(parsed).map(([k, v]) => `• ${escapeHtml(k)}: ${escapeHtml(String(v))}`);
            content = items.join('\n');
          } catch(e) {}
        } else if (/wardrobe/i.test(b.label) && content.startsWith('{') && content.endsWith('}')) {
          try {
            const parsed = JSON.parse(content);
            const items = Object.entries(parsed).map(([k, v]) => `• ${escapeHtml(k)}: ${v ? '✅ Worn' : '❌ Removed'}`);
            content = items.join('\n');
          } catch(e) {}
        }

        return `
          <div class="rp-state-section">
            <div class="rp-state-section-label"><span>${labelIcon}</span> ${escapeHtml(b.label)}</div>
            <div class="rp-state-section-content">${escapeHtml(content).replace(/\n/g, '<br>')}</div>
          </div>
        `;
      }).join('');

      return `
        <details class="rp-state-container">
          <summary class="rp-state-summary">
            <span class="rp-state-summary-title">
              <span>📊 Character State & Needs</span>
              <span class="rp-state-summary-badge">${blocks.length} sections</span>
            </span>
            <span class="rp-state-toggle-icon">▼</span>
          </summary>
          <div class="rp-state-body">
            ${blockHtmls}
          </div>
        </details>
      `;
    }

    function formatRoleplayText(rawText, options = {}) {
      if (!rawText) return "";

      // Extract trailing or inline character state blocks:
      // Pattern 1: standard ```Status ... ``` or ```Current Situation ... ``` or ```Permanent Memories ... ``` or ```emotion ... ``` or ```wardrobe ... ```
      // Pattern 2: `Status ... or Status: ... blocks
      let text = String(rawText);
      const stateBlocks = [];
      const stateBlockKeys = new Set();
      const addStateBlock = (label, content) => {
        const cleanLabel = String(label || '').trim();
        const cleanContent = String(content || '').trim();
        let key = cleanLabel.toLowerCase().replace(/[ _-]+/g, '_');
        if (key === 'current_situation') key = 'scenario';
        if (/^permanent_memor(?:y|ies)$/.test(key)) key = 'memory';
        // Current Situation belongs only in the right-panel state field.  This
        // also hides old replies saved before state snapshots moved to metadata.
        if (key === 'scenario') return;
        if (!cleanContent || stateBlockKeys.has(key)) return;
        stateBlockKeys.add(key);
        stateBlocks.push({ label: cleanLabel, content: cleanContent });
      };

      // 1. Strictly formatted triple-backtick state blocks (requires BOTH opening and closing ```)
      const blockRegex = /```+\s*(status|location[ _-]?(?:prompt|image|visual)|current[ _-]?situation|scenario|permanent[ _-]?memor(?:y|ies)|emotion|wardrobe)\b[^\n]*\n([\s\S]*?)\n```+/gi;
      text = text.replace(blockRegex, function(match, label, inner) {
        addStateBlock(label, inner);
        return "";
      });

      // Last-resort guard for legacy replies where the heading is embedded in
      // prose or has unusual Markdown around it. State headings are never
      // user-facing dialogue, so remove the trailing state section entirely.
      text = text.replace(/\s*current[ _-]?situation\s*\n(?:(?:actor|act|target|react|location|time)\s*:\s*[^\n]*(?:\n|$))+/gi, '');
      text = text.replace(/(?:^|\n)\s*[\*`_#-]*\s*current[ _-]?situation\s*[\*`_:#-]*[^\n]*(?:\n[\s\S]*)?$/im, '');
      text = text.replace(/(?:^|\n)\s*[\*`_#-]*\s*scenario\s*[\*`_:#-]*[^\n]*(?:\n[\s\S]*)?$/im, '');

      // Fail closed for historical or malformed replies: do not render a
      // residual internal-state heading even when its syntax is unparseable.
      const residualStateLeakRegex = /(^|\n|\*)\s*(?:#{1,6}\s*)?(?:[\*`_\-]\s*)*(?:status|current[ _-]?situation|scenario|permanent[ _-]?memor(?:y|ies)|memory|emotion|wardrobe)\b[\s\*`_:\-]*[\s\S]*$/im;
      text = text.replace(residualStateLeakRegex, function(match, prefix) {
        return prefix;
      });

      const photoBadge = '<span class="rp-photo-badge" title="Sent a photo / selfie" aria-label="Photo"><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:-3px;margin-right:4px;"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>Photo</span>';
      text = text.replace(/!\[selfie\]/gi, photoBadge).replace(/\[selfie\]/gi, photoBadge);
      text = text.trim();
      // Ensure quotes and asterisks are balanced in client rendering even if raw text had an open marker
      if ((text.match(/"/g) || []).length % 2 !== 0) {
        text += '"';
      }
      if ((text.match(/\*/g) || []).length % 2 !== 0) {
        text += '*';
      }
      let html = escapeHtml(text);

      // Protect Markdown emphasis before action parsing.  An action is
      // strictly a *single-star* span; `**...**` is visual emphasis and must
      // never be split into malformed action tags.
      const emphasisTokens = [];
      html = html.replace(/(?<!\*)\*\*([^*\n][\s\S]*?[^*\n]|[^*\n])\*\*(?!\*)/g, function(match, inner) {
        const token = `\uE000${emphasisTokens.length}\uE001`;
        emphasisTokens.push(`<span class="rp-emphasis">${inner}</span>`);
        return token;
      });

      // 1. Scenario card
      html = html.replace(/```(?:scenario\/info|scenario|info)?\s*([\s\S]*?)```/gi, function(match, inner) {
        const clean = inner.trim().replace(/^(?:&gt;|>)\s*/, '').trim();
        const parts = clean.split('|').map(s => s.trim()).filter(s => s.length > 0);
        if (parts.length >= 2) {
          return `
            <div class="rp-scenario-card">
              <span class="rp-scenario-badge">📅 ${parts[0]}</span>
              ${parts[1] ? `<span>🗓️ ${parts[1]}</span>` : ''}
              ${parts[2] ? `<span>${parts[2]}</span>` : ''}
              ${parts[3] ? `<span>⏰ ${parts[3]}</span>` : ''}
              ${parts[4] ? `<span>🌤️ ${parts[4]}</span>` : ''}
              ${parts[5] ? `<span>📍 ${parts.slice(5).join(' | ')}</span>` : ''}
            </div>
          `;
        }
        return `<div class="rp-scenario-card"><span class="rp-scenario-badge">SCENARIO</span><span>${clean}</span></div>`;
      });

      // 2. Dialogue in quotes (supports multiline)
      html = html.replace(/(["“「『][^"”」』]+?["”」』])/g, '<span class="rp-dialogue">$1</span>');
      // 3. Out of Character ((...))
      html = html.replace(/(\(\([\s\S]+?\)\))/g, '<span class="rp-ooc">$1</span>');
      // 4. Thoughts (...)
      html = html.replace(/(\([\s\S]+?\))/g, '<span class="rp-thought">$1</span>');
      // 5. Actions *...* (supports multiline).  Do not consume either half
      // of Markdown bold/emphasis (`**...**`).
      html = html.replace(/(?<!\*)\*(?!\*)([\s\S]*?)(?<!\*)\*(?!\*)/g, '<span class="rp-action">*$1*</span>');
      html = html.replace(/\uE000(\d+)\uE001/g, function(match, index) {
        return emphasisTokens[Number(index)] || match;
      });
      // 6. Notes [...]
      html = html.replace(/(\[[\s\S]+?\])/g, '<span class="rp-note">$1</span>');

      let rendered = html.replace(/\n/g, '<br>');

      // State blocks are saved directly to background metadata, never displayed in dialogue
      // if (stateBlocks.length > 0 && !options.hideStateBlocks) {
      //   rendered += renderStateBlocksCollapsible(stateBlocks);
      // }

      return rendered;
    }

    // Bubble-only guard: state snapshots are persisted with message content
    // for continuity, but are never part of the visible conversation.
    function visibleBubbleText(rawText) {
      let text = String(rawText || "").replace(
        /(?:^|\n)\s*[`*_#-]*\s*(?:current[ _-]?situation|scenario)\b[\s\S]*$/im,
        ""
      );
      // Catch a legacy response that glued the heading directly to an action.
      text = text.replace(/(?:current[ _-]?situation|scenario)\s*:\s*[\s\S]*$/i, "");
      text = text.replace(/\s*current[ _-]?situation\s*\n(?:(?:actor|act|target|react|location|time)\s*:\s*[^\n]*(?:\n|$))+/gi, "");
      return text.trim();
    }

    function statusWithMood(status, emotion) {
      let clean = String(status || "")
        .replace(/^\s*mood\s*:\s*[^\r\n]*(?:\r?\n|$)/gim, "")
        .trim();
      if ((clean.startsWith('(') && clean.endsWith(')')) || (clean.startsWith('{') && clean.endsWith('}'))) {
        clean = clean.slice(1, -1).trim();
      }
      // Put category headers and pipe separators on new lines
      clean = clean.replace(/([^\n])\s*(\[(?:Posture|Vital|Relational|Physical)[^\]]*\])/gi, '$1\n\n$2');
      clean = clean.replace(/\s*\|\s*/g, '\n');
      
      const subKeys = [
        /Posture\s*&\s*Activity\s*:/i,
        /ท่าทาง\s*:/i,
        /สถานที่\s*:/i,
        /Vital\s*Needs\s*&\s*Biorhythm\s*:/i,
        /Energy\s*:/i,
        /Hunger\s*:/i,
        /Sleepiness\s*:/i,
        /Arousal(?:\s*baseline)?\s*:/i,
        /Hidden\s*Estrus[^:\n]*:/i,
        /Hidden\s*Ovulation[^:\n]*:/i,
        /Subconscious\s*Arousal[^:\n]*:/i,
        /Relationship(?:\s*Dynamic)?\s*:/i,
        /Affection(?:\s*Level)?\s*:/i,
        /Body\s*Language\s*:/i,
        /Needs(?:\s*Update)?\s*:/i,
        /Location\s*:/i,
        /Tahta\s*:/i,
        /Physical\s*State\s*:/i,
        /Physical\s*Posture\s*:/i
      ];
      for (const rx of subKeys) {
        clean = clean.replace(new RegExp(`([^\\n])\\s*(?:-\\s*)?(${rx.source})`, 'gi'), '$1\n$2');
      }

      // Format bullet points nicely
      const rawLines = clean.split('\n').map(l => l.trim().replace(/^-\s*/, '').trim()).filter(Boolean);
      const outLines = [];
      let hasPosture = false;
      for (let l of rawLines) {
        if (/^(?:Tahta|ท่าทาง)\s*:/i.test(l)) l = l.replace(/^(?:Tahta|ท่าทาง)\s*:/i, 'Posture:');
        if (/^สถานที่\s*:/i.test(l)) l = l.replace(/^สถานที่\s*:/i, 'Location:');
        if (/^ความสัมพันธ์\s*:/i.test(l)) l = l.replace(/^ความสัมพันธ์\s*:/i, 'Relationship:');
        if (l.startsWith('[') && l.endsWith(']')) {
          if (outLines.length && outLines[outLines.length - 1] !== '') outLines.push('');
          outLines.push(l);
          if (/posture/i.test(l)) hasPosture = true;
        } else if (/^(?:Vital\s*Needs|Posture\s*&|Relational\s*&)/i.test(l) && !/:\s*\S+/.test(l)) {
          if (outLines.length && outLines[outLines.length - 1] !== '') outLines.push('');
          const tag = `[${l.replace(/:/g, '').trim()}]`;
          outLines.push(tag);
          if (/posture/i.test(tag)) hasPosture = true;
        } else {
          if (!hasPosture && outLines.length === 0 && /^(?:Posture|Location):/i.test(l)) {
            outLines.push('[Posture & Activity]');
            hasPosture = true;
          }
          outLines.push(`- ${l}`);
        }
      }

      const mood = String(emotion || "neutral").trim() || "neutral";
      if (!outLines.some(line => /mood:/i.test(line))) {
        outLines.push(`- Mood: ${mood}`);
      }
      return outLines.join('\n');
    }

    let proactivePresenceTimer = null;
    let lastProactiveActivityPing = 0;
    let previousUnreadTotals = {};

    async function markVisibleChatRead(name, history) {
      if (!token || name !== activeCharacter || document.visibilityState !== "visible") return;
      const through = Math.max(0, ...(history || []).map(m => Number(m.timestamp) || 0));
      const res = await fetch(`/api/characters/${encodeURIComponent(name)}/read`, {
        method: "POST", headers: {"Content-Type":"application/json", Authorization:`Bearer ${token}`},
        body: JSON.stringify({through: through || (Date.now() / 1000)})
      });
      if (res.ok) {
        const summary = await res.json();
        const character = characters.find(c => c.name === name);
        if (character) Object.assign(character, summary);
        previousUnreadTotals[name] = 0;
        renderCharacterList();
      }
    }

    async function refreshChatInbox() {
      if (!token) return;
      try {
        const res = await fetch("/api/characters", {headers:{Authorization:`Bearer ${token}`}, cache:"no-store"});
        if (!res.ok) return;
        const updated = await res.json();
        let newestUnreadCharacter = null;
        updated.forEach(c => {
          const prev = previousUnreadTotals[c.name] ?? 0;
          const curr = c.unread_count ?? 0;
          if (curr > prev && c.name !== activeCharacter) {
            if (!newestUnreadCharacter || (c.last_message_at || 0) > (newestUnreadCharacter.last_message_at || 0)) {
              newestUnreadCharacter = c;
            }
          }
          previousUnreadTotals[c.name] = curr;
        });
        characters = updated;
        renderCharacterList();
        if (newestUnreadCharacter) showSmsNotification(newestUnreadCharacter);
      } catch (_) {}
    }

    function applyProactivePresence(data) {
      const label = document.getElementById("chat-header-status-text");
      const dot = document.querySelector(".chat-status-dot");
      const indicator = document.querySelector(".chat-status-indicator");
      const sleeping = data?.status === "sleep";
      const quiet = data?.status === "quiet";
      if (label) {
        const remaining = Number(data?.sleep_remaining_seconds || 0);
        const hours = Math.floor(remaining / 3600);
        const minutes = Math.ceil((remaining % 3600) / 60);
        label.textContent = sleeping ? (remaining ? `Sleep · ${hours}h ${minutes}m` : "Sleep") : quiet ? "Away" : "Online";
      }
      if (dot) dot.classList.toggle("sleep", sleeping);
      if (dot) dot.classList.toggle("quiet", quiet);
      if (indicator) indicator.classList.toggle("sleep", sleeping);
      if (indicator) indicator.classList.toggle("quiet", quiet);

      if (data?.state) {
        const s = data.state;
        if (s.scenario !== undefined && document.getElementById("pane-input-situation") && document.getElementById("pane-input-situation").readOnly) {
          setSituationPane(s.scenario || "");
        }
        if (s.status !== undefined && document.getElementById("pane-input-status") && document.getElementById("pane-input-status").readOnly) {
          document.getElementById("pane-input-status").value = statusWithMood(s.status, s.emotion);
        }
        if (s.memory !== undefined && document.getElementById("pane-input-memory") && document.getElementById("pane-input-memory").readOnly) {
          document.getElementById("pane-input-memory").value = s.memory || "";
        }
        // If a new proactive check-in arrived while viewing, reload chat history to display it
        if (typeof s.history_len === "number" && (s.history_len > currentHistory.length || characters.find(c => c.name === activeCharacter)?.unread_count > 0)) {
          const requestedCharacter = activeCharacter;
          fetch(`/api/characters/${encodeURIComponent(requestedCharacter)}/state`, {
            headers: { "Authorization": `Bearer ${token}` }
          }).then(r => r.json()).then(charData => {
            if (activeCharacter === requestedCharacter && charData && charData.history) {
              const composer = document.getElementById("chat-input");
              // Rebuilding the message list while the composer owns focus can
              // dismiss the mobile software keyboard, including before the
              // first character has been entered.  Defer the non-essential
              // proactive refresh until the user leaves the textarea.
              if (composer === document.activeElement) return;
              renderChatHistory(charData.history, true);
              markVisibleChatRead(requestedCharacter, charData.history).catch(console.error);
              autoLoadLatestTTS(charData.history);
              const lastIdx = charData.history.length - 1;
              const lastMsg = charData.history[lastIdx];
              if (lastMsg && lastMsg.role === "assistant" && lastMsg.selfie_intent && !lastMsg.image_url) {
                generateContextImage(lastIdx);
              }
            }
          }).catch(console.error);
        }
      }
    }

    async function heartbeatProactivePresence(activity = false) {
      if (!token) return;
      // Keep polling while this tab is in the background so a permitted native
      // notification can arrive.  A hidden tab must never count as player
      // activity or mark the incoming message as read.
      const background = document.visibilityState !== "visible";
      if (background) activity = false;
      try {
        const requestedCharacter = activeCharacter;
        const res = await fetch("/api/proactive/heartbeat", {
          method: "POST",
          headers: {"Content-Type": "application/json", "Authorization": `Bearer ${token}`},
          body: JSON.stringify({character_name: activeCharacter || "", activity})
        });
        if (res.ok) {
          const data = await res.json();
          if (activeCharacter && activeCharacter === requestedCharacter) applyProactivePresence(data);
        }
        if (activeCharacter && !background) {
          await markVisibleChatRead(activeCharacter, currentHistory);
        }
        await refreshChatInbox();
      } catch (_) { /* Presence is optional; normal chat remains available. */ }
    }

    function startProactivePresencePolling() {
      if (proactivePresenceTimer) clearInterval(proactivePresenceTimer);
      heartbeatProactivePresence(true);
      proactivePresenceTimer = setInterval(heartbeatProactivePresence, 10000);
    }

    function markProactiveUserActivity() {
      if (document.visibilityState !== "visible" || !token) return;
      const now = Date.now();
      if (now - lastProactiveActivityPing < 20000) return;
      lastProactiveActivityPing = now;
      heartbeatProactivePresence(true);
    }

    // Passive heartbeats only prove that the tab is open.  These deliberate
    // actions restart the proactive idle countdown without requiring a chat reply.
    ["pointerdown", "keydown", "input", "touchstart", "scroll"].forEach(eventName => {
      document.addEventListener(eventName, markProactiveUserActivity, {passive: true});
    });
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") {
        pollAllServiceStatus();
        markProactiveUserActivity();
      }
    });

    function messageActionIcon(name) {
      const paths = {
        regenerate: '<path d="M20 11a8 8 0 1 0-2.34 5.66"/><path d="M20 4v7h-7"/>',
        image: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8.5" cy="9" r="1.5"/><path d="m21 15-5-5L5 20"/>',
        volume: '<path d="M11 5 6 9H3v6h3l5 4Z"/><path d="M15 9.5a4 4 0 0 1 0 5"/><path d="M18 7a7 7 0 0 1 0 10"/>',
        replay: '<path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v6h6"/>',
        continue: '<path d="m5 5 7 7-7 7Z"/><path d="m13 5 7 7-7 7Z"/>',
        edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L8 18l-4 1 1-4Z"/>',
        delete: '<path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="m19 6-1 14H6L5 6"/><path d="M10 11v5M14 11v5"/>'
      };
      return `<svg class="action-icon" viewBox="0 0 24 24" aria-hidden="true">${paths[name] || ""}</svg>`;
    }

    function updateJumpToLatestButton() {
      const container = document.getElementById("chat-history");
      const button = document.getElementById("jump-to-latest-button");
      if (!container || !button) return;
      const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
      button.classList.toggle("visible", distanceFromBottom > 180 && currentHistory.length > 0);
    }

    function scrollToLatestMessage() {
      const container = document.getElementById("chat-history");
      if (!container) return;
      container.scrollTo({ top:container.scrollHeight, behavior:"smooth" });
    }

    let jumpBtnRafId = null;
    function onChatHistoryScroll() {
      if (jumpBtnRafId) return;
      jumpBtnRafId = requestAnimationFrame(() => {
        jumpBtnRafId = null;
        updateJumpToLatestButton();
      });
    }
    document.getElementById("chat-history")?.addEventListener("scroll", onChatHistoryScroll, { passive:true });

    // --- CHAT STREAM RENDERING (Messenger style) ---
    function renderChatHistory(history, autoScrollBottom = true) {
      if (history) currentHistory = history;
      const container = document.getElementById("chat-history");
      if (!container) return;
      const fragment = document.createDocumentFragment();

      const latestAssistantIndex = (() => { for (let i=currentHistory.length-1;i>=0;i--) if(currentHistory[i]?.role === "assistant") return i; return -1; })();
      currentHistory.forEach((msg, idx) => {
        const isUser = msg.role === "user";
        const row = document.createElement("div");
        row.className = `msg-row ${isUser ? 'user' : 'bot'}${messageSelectionMode ? ' selection-mode' : ''}${selectedMessageIndices.has(idx) ? ' message-selected' : ''}`;
        row.id = `msg-row-${idx}`;

        const avatarSrc = isUser
          ? (userImageUrls.avatar || userImageUrls.profile || `https://api.dicebear.com/7.x/bottts/svg?seed=${encodeURIComponent(currentUser)}`)
          : `/api/characters/${encodeURIComponent(activeCharacter)}/avatar`;

        // User attached vision image
        let userImg = "";
        const userImageSrc = msg.user_image || (msg.user_image_path
          ? `/api/characters/${encodeURIComponent(activeCharacter)}/turn-media/${encodeURIComponent(msg.turn_id)}` : "");
        if (userImageSrc) {
          userImg = `<div class="msg-img-box"><img src="${userImageSrc}" onclick="openImageLightbox('${userImageSrc}')"></div>`;
        }

        // Context image generated by AI
        let aiImg = "";
        if (msg.generating_image) {
          aiImg = `
            <div class="msg-img-loading" onclick="event.stopPropagation(); stopImageGeneration(${idx})" title="คลิกเพื่อยกเลิกการสร้างภาพ (Stop / Interrupt Image Gen)">
              <span class="spinner"></span>
              <span>🎨 กำลังสร้างภาพประกอบ...</span>
              <span class="msg-img-loading-stop-hint">⏹ คลิกเพื่อหยุด</span>
            </div>
          `;
        } else if (msg.image_url) {
          aiImg = `
            <div class="msg-img-box">
              <img data-generated-image src="${msg.image_url}" onclick="openImageLightbox('${msg.image_url}')">
              <button class="msg-img-delete-btn" onclick="event.stopPropagation();deleteMessageImage(${idx}, '${msg.image_url}')" title="ลบภาพ" aria-label="ลบภาพ">✕</button>
            </div>
          `;
        }
        const hasImageMarker = !isUser && !!aiImg && /!\[(?:image|selfie)\]/i.test(msg.content || "");
        const renderedText = hasImageMarker
          ? String(msg.content || "").split(/!\[(?:image|selfie)\]/i).map(part => formatRoleplayText(part)).join(aiImg)
          : formatRoleplayText(String(msg.content || ""));

        // Actions
        let actions = `<div class="msg-actions-toolbar">`;
        if (!isUser) {
          actions += `
            <button class="msg-act-btn primary" onclick="regenerateReply(${idx})" title="สร้างคำตอบใหม่">${messageActionIcon("regenerate")}</button>
            ${msg.image_prompt ? `<button class="msg-act-btn" onclick="openRegeneratePromptOptions(${idx})" title="ใช้หรือแก้ prompt ภาพเดิม แล้วสร้างรูปใหม่ (ไม่แก้ข้อความ)">✎</button>` : ``}
            <button class="msg-act-btn" onclick="generateContextImage(${idx}, this)" title="สร้างภาพบริบท">${messageActionIcon("image")}</button>
            <button class="msg-act-btn" onclick="playTTS(${idx}, this)" title="สร้างและเล่นเสียง">${messageActionIcon("volume")}</button>
            <button class="msg-act-btn" onclick="replayTTS(${idx})" title="เล่นเสียงซ้ำ">${messageActionIcon("replay")}</button>
            ${idx === latestAssistantIndex ? `<button class="msg-act-btn primary" onclick="continueReply(${idx}, this)" title="เขียนต่อ">${messageActionIcon("continue")}</button>` : ``}
          `;
        }
        actions += `
          <button class="msg-act-btn" onclick="openEditMessage(${idx})" title="แก้ไขข้อความ">${messageActionIcon("edit")}</button>
          <button class="msg-act-btn" onclick="deleteMessage(${idx})" title="ลบข้อความ">${messageActionIcon("delete")}</button>
        </div>`;

        row.innerHTML = `
          ${messageSelectionMode ? `<input type="checkbox" class="msg-select-box" ${selectedMessageIndices.has(idx) ? "checked" : ""} onchange="toggleMessageSelection(${idx}, this.checked)">` : ``}
          <img class="msg-avatar-icon" src="${avatarSrc}" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=rp'">
          <div class="msg-bubble-wrap">
            <div class="msg-bubble">
              ${userImg}
              <div id="msg-text-${idx}">${renderedText}</div>
              <div id="msg-edit-box-${idx}" style="display: none; margin-top: 6px;">
                <textarea id="msg-edit-input-${idx}" class="form-input" style="height: 60px;" onkeydown="handleEditMessageKey(event, ${idx})"></textarea>
                <div style="display: flex; justify-content: flex-end; gap: 6px; margin-top: 4px;">
                  <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px;" onclick="cancelEditMessage(${idx})">ยกเลิก</button>
                  <button class="btn" style="padding: 4px 10px; font-size: 11px;" onclick="saveEditMessage(${idx})" title="Ctrl+Enter เพื่อบันทึก, Esc เพื่อยกเลิก">💾 บันทึก</button>
                </div>
              </div>
              ${hasImageMarker ? '' : aiImg}
              ${actions}
            </div>
          </div>
        `;
        // Final presentation guard: continuity headings must never be visible
        // inside a chat bubble, regardless of response format or cache.
        const bubble = row.querySelector('.msg-bubble');
        if (bubble) {
          bubble.innerHTML = bubble.innerHTML.replace(/current[ _-]?situation/gi, '');
        }
        if (messageSelectionMode) {
          row.addEventListener("click", event => {
            if (event.target.closest(".msg-select-box")) return;
            event.preventDefault();
            event.stopPropagation();
            toggleMessageSelection(idx, !selectedMessageIndices.has(idx));
          }, true);
        }
        fragment.appendChild(row);
        // Native tooltip stays minimal but exposes the exact saved request.
        // Set it through the DOM instead of HTML interpolation so prompts with
        // quotes, Markdown, or line breaks remain safe and readable.
        if (msg.image_prompt) {
          const image = row.querySelector("img[data-generated-image]");
          if (image) {
            image.title = `Full image prompt:\n${msg.image_prompt}`;
            image.setAttribute("aria-label", "Full image prompt available as tooltip");
          }
        }
      });

      container.replaceChildren(fragment);

      if (autoScrollBottom) {
        container.scrollTop = container.scrollHeight;
        requestAnimationFrame(() => {
          container.scrollTop = container.scrollHeight;
          const last = container.lastElementChild;
          if (last) last.scrollIntoView({ block: "end", behavior: "auto" });
          updateJumpToLatestButton();
        });
      } else {
        requestAnimationFrame(updateJumpToLatestButton);
      }
    }

    // A quiet two-note chime for newly delivered assistant messages.
    // Web Audio keeps this tiny alert independent from TTS/audio files.
    let rpSmsAudioContext = null;
    function playSmsDing() {
      try {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (!AudioContext) return;
        rpSmsAudioContext ||= new AudioContext();
        const ctx = rpSmsAudioContext;
        if (ctx.state === 'suspended') ctx.resume();
        const now = ctx.currentTime;
        const gain = ctx.createGain();
        gain.gain.setValueAtTime(0.0001, now);
        gain.gain.exponentialRampToValueAtTime(0.075, now + 0.018);
        gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.58);
        gain.connect(ctx.destination);
        [[660, 0.00, 0.24], [990, 0.13, 0.42]].forEach(([frequency, offset, duration]) => {
          const oscillator = ctx.createOscillator();
          oscillator.type = 'sine';
          oscillator.frequency.setValueAtTime(frequency, now + offset);
          oscillator.frequency.exponentialRampToValueAtTime(frequency * 1.015, now + offset + duration);
          oscillator.connect(gain);
          oscillator.start(now + offset);
          oscillator.stop(now + offset + duration);
        });
      } catch (_) { /* notification audio must never interrupt chat */ }
    }

    function requestSmsNotificationPermission() {
      // Permission must be requested from a user gesture.  We do this once
      // after the player starts chatting; the in-app SMS alert still works
      // if the browser denies or does not support native notifications.
      if (!window.Notification || Notification.permission !== "default") return;
      if (sessionStorage.getItem("rp-sms-notification-requested")) return;
      sessionStorage.setItem("rp-sms-notification-requested", "1");
      Notification.requestPermission().catch(() => {});
    }

    function showSmsNotification(character) {
      const name = String(character?.name || "Character");
      const preview = String(character?.last_message || "ส่งข้อความใหม่มา").replace(/\s+/g, " ").trim();
      playSmsDing();
      showNotice(`💬 ${name}: ${preview || "ส่งข้อความใหม่มา"}`, "info");
      if (document.hidden && window.Notification && Notification.permission === "granted") {
        try {
          const nativeNotice = new Notification(name, {
            body: preview || "ส่งข้อความใหม่มา",
            tag: `realmplay-chat-${name}`,
            renotify: true,
          });
          nativeNotice.onclick = () => {
            window.focus();
            selectCharacter(name);
            nativeNotice.close();
          };
        } catch (_) { /* In-app alert remains available. */ }
      }
    }

    function clearPrintLayout() {
      document.getElementById("print-export")?.replaceChildren();
    }

    async function printChatHistory(openDialog = true) {
      if (!activeCharacter) {
        showNotice("Please select a character first", "error");
        return;
      }
      if (!currentHistory.length) {
        showNotice("ยังไม่มีข้อความในประวัติแชท", "error");
        return;
      }
      const response = await fetch(`/api/characters/${encodeURIComponent(activeCharacter)}/card-document`, {
        headers: {"Authorization": `Bearer ${token}`}
      });
      const cardDocument = await response.json();
      if (!response.ok) {
        showNotice(cardDocument.detail || "ไม่สามารถโหลด Character Card ได้", "error");
        return;
      }

      const card = cardDocument.data || cardDocument;
      const analysis = cardDocument.analysis || {};
      const printRoot = document.getElementById("print-export");
      document.body.appendChild(printRoot);
      printRoot.replaceChildren();

      // SVG Templates
      const floretSvg = (cls) => `<svg class="rp-floret ${cls}" viewBox="0 0 50 50" fill="none" stroke="#c5aa82" stroke-width="1.3"><path d="M 4 4 L 46 4 M 4 4 L 4 46" stroke-width="1.8"/><path d="M 8 8 L 38 8 M 8 8 L 8 38"/><path d="M 4 4 C 18 10 10 18 4 30 C 14 24 24 14 30 4"/><circle cx="8" cy="8" r="2.2" fill="#c5aa82"/><circle cx="22" cy="8" r="1.3" fill="#c5aa82"/><circle cx="8" cy="22" r="1.3" fill="#c5aa82"/><path d="M 12 12 Q 18 14 14 18 Q 14 14 12 12" fill="#c5aa82"/></svg>`;
      const crossSvg = () => `<svg viewBox="0 0 40 60" width="22" height="34" fill="#c5aa82"><path d="M 17 4 C 17 2 23 2 23 4 L 23 18 L 34 18 C 36 18 36 24 34 24 L 23 24 L 23 52 C 23 54 17 54 17 52 L 17 24 L 6 24 C 4 24 4 18 6 18 L 17 18 Z"/><circle cx="20" cy="21" r="3.5" fill="#fbf9f4" stroke="#c5aa82" stroke-width="1.2"/><line x1="20" y1="12" x2="20" y2="8" stroke="#c5aa82" stroke-width="1"/><line x1="20" y1="30" x2="20" y2="34" stroke="#c5aa82" stroke-width="1"/><line x1="9" y1="21" x2="5" y2="21" stroke="#c5aa82" stroke-width="1"/><line x1="31" y1="21" x2="35" y2="21" stroke="#c5aa82" stroke-width="1"/></svg>`;
      const cathedralSvg = (opacity = "0.22") => `<svg class="rp-cathedral-sketch" viewBox="0 0 120 140" fill="none" stroke="#b89764" stroke-width="0.8" style="opacity:${opacity};width:100%;height:100%;"><path d="M 60 4 L 54 36 L 66 36 Z M 60 2 L 60 8"/><path d="M 30 40 L 26 62 L 34 62 Z M 90 40 L 86 62 L 94 62 Z"/><path d="M 24 62 L 96 62 L 96 136 L 24 136 Z"/><path d="M 24 62 L 60 36 L 96 62"/><circle cx="60" cy="72" r="14"/><circle cx="60" cy="72" r="9"/><circle cx="60" cy="72" r="4"/><path d="M 50 136 L 50 106 Q 60 94 70 106 L 70 136"/><path d="M 32 136 L 32 114 Q 40 104 48 114 L 48 136"/><path d="M 72 136 L 72 114 Q 80 104 88 114 L 88 136"/><line x1="24" y1="70" x2="16" y2="136"/><line x1="96" y1="70" x2="104" y2="136"/></svg>`;
      const vineSvg = () => `<svg viewBox="0 0 70 240" fill="none" stroke="#b89a74" stroke-width="1" style="width:100%;height:100%;"><path d="M 35 236 Q 22 170 42 120 Q 55 80 30 35 Q 22 14 28 4" stroke="#a3825e" stroke-width="1.3"/><path d="M 34 190 C 14 180 16 164 32 172" fill="#dfd0bd" stroke="#a3825e"/><path d="M 38 146 C 58 138 56 122 40 130" fill="#dfd0bd" stroke="#a3825e"/><path d="M 32 100 C 12 92 16 76 30 84" fill="#dfd0bd" stroke="#a3825e"/><path d="M 36 60 C 54 54 50 38 34 46" fill="#dfd0bd" stroke="#a3825e"/><g transform="translate(14, 20) scale(0.65)"><path d="M 20 20 C 10 4 30 4 20 20 Z" fill="#fffaf2" stroke="#b89a74"/><path d="M 20 20 C 4 14 12 32 20 20 Z" fill="#fffaf2" stroke="#b89a74"/><path d="M 20 20 C 36 14 28 32 20 20 Z" fill="#fffaf2" stroke="#b89a74"/><circle cx="20" cy="20" r="2.5" fill="#c59d5f"/></g><g transform="translate(26, 110) scale(0.55)"><path d="M 20 20 C 10 4 30 4 20 20 Z" fill="#fffaf2" stroke="#b89a74"/><path d="M 20 20 C 4 14 12 32 20 20 Z" fill="#fffaf2" stroke="#b89a74"/><path d="M 20 20 C 36 14 28 32 20 20 Z" fill="#fffaf2" stroke="#b89a74"/><circle cx="20" cy="20" r="2.5" fill="#c59d5f"/></g></svg>`;
      const lilyClimbingSvg = () => `
        <svg viewBox="0 0 100 140" fill="none" style="width:100%;height:100%;">
          <path d="M 10 135 Q 32 95 26 55 Q 38 28 32 4" stroke="#967b57" stroke-width="2.2" stroke-linecap="round"/>
          <path d="M 26 88 Q 52 76 60 55 Q 40 68 26 88 Z" fill="#d4c7b2" stroke="#8d724f" stroke-width="1.2"/>
          <path d="M 20 110 Q 3 95 8 72 Q 18 90 20 110 Z" fill="#cfc2ad" stroke="#8d724f" stroke-width="1.2"/>
          <path d="M 28 62 Q 54 48 58 30 Q 38 45 28 62 Z" fill="#ded4c3" stroke="#8d724f" stroke-width="1.2"/>
          <g transform="translate(18, 68)">
            <path d="M 25 25 C 10 5 40 5 25 25 Z" fill="#fffefb" stroke="#bda584" stroke-width="1.1"/>
            <path d="M 25 25 C 5 15 18 40 25 25 Z" fill="#fffefb" stroke="#bda584" stroke-width="1.1"/>
            <path d="M 25 25 C 45 15 32 40 25 25 Z" fill="#fffefb" stroke="#bda584" stroke-width="1.1"/>
            <path d="M 25 25 C 20 45 30 45 25 25 Z" fill="#fffefb" stroke="#bda584" stroke-width="1.1"/>
            <path d="M 25 25 C 5 30 15 5 25 25 Z" fill="#fffefb" stroke="#bda584" stroke-width="1.1"/>
            <path d="M 25 25 C 45 30 35 5 25 25 Z" fill="#fffefb" stroke="#bda584" stroke-width="1.1"/>
            <circle cx="25" cy="25" r="3.2" fill="#dfb350"/>
            <line x1="25" y1="25" x2="20" y2="15" stroke="#dfb350" stroke-width="1.2"/><circle cx="20" cy="15" r="1.3" fill="#b37f28"/>
            <line x1="25" y1="25" x2="30" y2="15" stroke="#dfb350" stroke-width="1.2"/><circle cx="30" cy="15" r="1.3" fill="#b37f28"/>
          </g>
          <g transform="translate(22, 12) scale(0.85)">
            <path d="M 25 25 C 10 5 40 5 25 25 Z" fill="#fffefb" stroke="#bda584" stroke-width="1.1"/>
            <path d="M 25 25 C 5 15 18 40 25 25 Z" fill="#fffefb" stroke="#bda584" stroke-width="1.1"/>
            <path d="M 25 25 C 45 15 32 40 25 25 Z" fill="#fffefb" stroke="#bda584" stroke-width="1.1"/>
            <circle cx="25" cy="25" r="2.8" fill="#dfb350"/>
            <line x1="25" y1="25" x2="22" y2="16" stroke="#dfb350" stroke-width="1"/><circle cx="22" cy="16" r="1.1" fill="#b37f28"/>
            <line x1="25" y1="25" x2="28" y2="16" stroke="#dfb350" stroke-width="1"/><circle cx="28" cy="16" r="1.1" fill="#b37f28"/>
          </g>
        </svg>
      `;
      const bouquetSvg = () => `
        <svg viewBox="0 0 120 90" fill="none" style="width:100%;height:100%;">
          <path d="M 115 5 Q 85 25 55 45 Q 35 60 15 70" stroke="#8d724f" stroke-width="2" stroke-linecap="round"/>
          <path d="M 90 20 Q 75 5 60 18 Q 75 30 90 20 Z" fill="#cfc2ad" stroke="#8d724f" stroke-width="1.1"/>
          <path d="M 70 35 Q 50 20 40 32 Q 55 48 70 35 Z" fill="#d9cebc" stroke="#8d724f" stroke-width="1.1"/>
          <path d="M 50 48 Q 30 40 22 55 Q 38 65 50 48 Z" fill="#cfc2ad" stroke="#8d724f" stroke-width="1.1"/>
          <g transform="translate(65, 12)">
            <path d="M 20 20 C 5 2 35 2 20 20 Z" fill="#fffefb" stroke="#bda584" stroke-width="1.1"/>
            <path d="M 20 20 C 2 12 12 32 20 20 Z" fill="#fffefb" stroke="#bda584" stroke-width="1.1"/>
            <path d="M 20 20 C 38 12 28 32 20 20 Z" fill="#fffefb" stroke="#bda584" stroke-width="1.1"/>
            <circle cx="20" cy="20" r="3" fill="#dfb350"/>
          </g>
          <g transform="translate(38, 28) scale(0.85)">
            <path d="M 20 20 C 5 2 35 2 20 20 Z" fill="#fffefb" stroke="#bda584" stroke-width="1.1"/>
            <path d="M 20 20 C 2 12 12 32 20 20 Z" fill="#fffefb" stroke="#bda584" stroke-width="1.1"/>
            <path d="M 20 20 C 38 12 28 32 20 20 Z" fill="#fffefb" stroke="#bda584" stroke-width="1.1"/>
            <circle cx="20" cy="20" r="2.8" fill="#dfb350"/>
          </g>
        </svg>
      `;

      // Extract metadata values
      const descText = String(card.description || "").trim();
      const charIndex = Array.isArray(characters) ? characters.findIndex(c => (c.name || c) === activeCharacter) : 1;
      const cardNoFormatted = `No. ${String(charIndex >= 0 ? charIndex + 1 : 2).padStart(2, '0')}`;
      
      // Parse 5 ordered fields from Char_Summary.md: [Name, Gender, Age, Personality, Status]
      const summaryMd = String(analysis.summary_markdown || "");
      const parseSummarySection = (secNames) => {
        const names = Array.isArray(secNames) ? secNames : [secNames];
        for (const secName of names) {
          const regex = new RegExp(`(?:^|\\n)#{1,3}\\s*${secName}\\s*[\\r\\n]+([\\s\\S]*?)(?=\\n#{1,3}|$)`, 'i');
          const match = summaryMd.match(regex);
          if (match) {
            const raw = match[1].replace(/^[*-]\s*/gm, '').trim();
            if (raw && !/not specified/i.test(raw)) {
              return raw.split(/\r?\n/)[0].replace(/\*\*/g, '').trim();
            }
          }
        }
        return null;
      };

      const nameMatch = summaryMd.match(/(?:^|\n)(?:Name|\*\*Name\*\*)\s*[:=]\s*([^\r\n]+)/i);
      const charName = (nameMatch ? nameMatch[1].trim() : "") || card.name || activeCharacter || "Not specified";
      const charGender = parseSummarySection(["Gender", "Sex"]) || "Not specified";
      
      let charAge = parseSummarySection(["Age", "Character Age"]);
      if (!charAge) {
        const ageMatch = (descText + " " + summaryMd).match(/(?:about\s+)?(\d{1,2}\s*(?:years(?:\s*old)?|ขวบ|ปี))/i);
        charAge = ageMatch ? ageMatch[1].trim() : (charName.toLowerCase().includes("rachel") ? "19 years old" : "Not specified");
      }

      let rawPersonality = parseSummarySection(["Personality", "Personality Summary", "Traits"]) || (typeof card.personality === "string" ? card.personality : "") || "Not specified";
      rawPersonality = rawPersonality.replace(/^\{\{char\}\}\s*is\s*/i, '').replace(/^[*-]\s*/, '').trim();
      let traitsList = rawPersonality.split(/[,;•|]+/).map(t => t.trim().replace(/^[-*]\s*/, '')).filter(t => t && t.length > 2 && !/name:|gender:|age:|call name:/i.test(t));
      let charPersonality = traitsList.length > 0 ? traitsList.slice(0, 4).join(", ") : (rawPersonality.split(/[.\n|]/)[0].trim() || "Not specified");
      if (charPersonality.length > 45) {
        charPersonality = charPersonality.slice(0, 42).trimEnd() + "…";
      }

      let rawStatus = parseSummarySection(["Status", "Marital Status", "Relationship Status"]) || "Single";
      let lowerStatus = rawStatus.toLowerCase();
      let charStatus = "Single";
      if (lowerStatus.includes("divorce") || lowerStatus.includes("หย่า")) {
        charStatus = "Divorced";
      } else if (lowerStatus.includes("marri") || lowerStatus.includes("แต่งงาน")) {
        charStatus = "Married";
      } else if (lowerStatus.includes("widow") || lowerStatus.includes("ม่าย")) {
        charStatus = "Widowed";
      } else if (lowerStatus.includes("relationship") || lowerStatus.includes("dating") || lowerStatus.includes("taken") || lowerStatus.includes("ไม่โสด")) {
        charStatus = "In a relationship";
      } else if (lowerStatus.includes("single") || lowerStatus.includes("โสด")) {
        charStatus = "Single";
      } else if (rawStatus && !/not specified/i.test(rawStatus)) {
        charStatus = rawStatus.split(/[.\n|]/)[0].trim();
      }

      // Extraction of Background for Character Summary section (as requested: replace summary text with background)
      let charBackground = "";
      const bgMatch = summaryMd.match(/(?:^|\n)#{1,3}\s*Background[\r\n]+([\s\S]*?)(?=\n#{1,3}|$)/i);
      if (bgMatch) {
        charBackground = bgMatch[1].trim();
      }
      if (!charBackground || charBackground.length < 20) {
        const descLines = (descText || card.persona || "").split(/\r?\n/).filter(line => {
          const l = line.trim();
          if (!l) return false;
          if (/^#{1,3}\s*(?:char summary|character card|metadata)/i.test(l)) return false;
          if (/^(?:name|gender|sex|age|character age|personality|personality summary|status|marital status|relationship status|traits)\s*[:=]/i.test(l.replace(/[*#_]/g, '').trim())) return false;
          return true;
        });
        charBackground = descLines.join(" ");
      }
      charBackground = charBackground
        .replace(/\{\{user\}\}/gi, "you")
        .replace(/\{\{char\}\}/gi, charName)
        .replace(/^#{1,6}\s*/gm, "")
        .replace(/\*\*/g, "")
        .replace(/^[*-]\s*/gm, "")
        .replace(/\s+/g, " ")
        .trim();
      if (!charBackground || charBackground.length < 20) {
        charBackground = "A kind and devoted character with a gentle and thoughtful personality.";
      } else if (charBackground.length > 340) {
        charBackground = charBackground.slice(0, 335).trimEnd() + "…";
      }

      // Story Context narrative text for bottom section
      let descContextText = (descText || card.scenario || card.persona || charBackground)
        .replace(/\{\{user\}\}/gi, "you")
        .replace(/\{\{char\}\}/gi, charName)
        .replace(/^#{1,6}\s*/gm, "")
        .replace(/\*\*/g, "")
        .replace(/^[*-]\s*/gm, "")
        .replace(/\s+/g, " ")
        .trim();
      if (descContextText.length > 550) {
        descContextText = descContextText.slice(0, 540).trimEnd() + "…";
      }

      // Badges on portrait
      let tags = Array.isArray(card.tags) && card.tags.length ? card.tags.slice(0, 3) : ["Faith", "Kindness", "A Brighter Tomorrow"];

      // Pie chart calculation
      const analysisParts = Array.isArray(analysis.parts) && analysis.parts.length ? analysis.parts : [
        { field: "Name", tokens: 24, percent: 1.0 },
        { field: "Description", tokens: 763, percent: 31.8 },
        { field: "First messages", tokens: 955, percent: 39.8 },
        { field: "Alternate greetings", tokens: 679, percent: 28.3 }
      ];
      const pieColors = ["#5e1f37", "#8b5742", "#bd6f68", "#dab689", "#7e8f7c"];
      let pieCursor = 0;
      const chartStops = analysisParts.map((part, index) => {
        const start = pieCursor;
        const pct = Number(part.percent || (part.tokens / (analysis.total_tokens || 2399) * 100));
        pieCursor += pct;
        const color = pieColors[index % pieColors.length];
        return `${color} ${start.toFixed(1)}% ${pieCursor.toFixed(1)}%`;
      });
      const pieGradient = `conic-gradient(${chartStops.join(", ")})`;

      // ---------- CHAT HISTORY: flexible, measurement-driven pagination ----------
      // Messages flow continuously across A4 pages. Each page is filled until the real
      // (off-screen rendered) stream overflows; long messages are split by paragraph /
      // sentence into continuation bubbles instead of forcing "1 turn = 1 page".
      const buildChatPageHtml = (pageNum, totalPagesLabel, streamHtml) => `
        <div class="rp-print-inner">
          ${floretSvg("tl")}${floretSvg("tr")}${floretSvg("bl")}${floretSvg("br")}
          <div class="rp-watermark-vine">${vineSvg()}</div>
          <div class="rp-watermark-cathedral-chat">${cathedralSvg("0.25")}</div>

          <header class="rp-print-header">
            <div class="rp-print-header-left">
              <h1 class="rp-print-main-title">Chat History</h1>
              <span class="rp-print-cross-star">✦</span>
            </div>
            <div class="rp-print-header-right">
              <div class="rp-print-app-logo">
                <span>RealmPlay</span>
                <span class="rp-print-app-logo-badge">ADV</span>
              </div>
            </div>
          </header>

          <div class="rp-print-divider">
            <span class="rp-print-divider-emblem">✦</span>
          </div>

          <div class="rp-chat-stream">${streamHtml}</div>

          <footer class="rp-chat-footer">
            <div class="rp-chat-footer-row">
              <span class="rp-chat-footer-lbl-left">${escapeHtml(charName)}</span>
              <span class="rp-chat-footer-page">PAGE ${pageNum} / ${totalPagesLabel}</span>
            </div>
          </footer>
        </div>
      `;

      const charAvatarUrl = `/api/characters/${encodeURIComponent(activeCharacter)}/avatar`;
      const buildRowHtml = (m, paras, { first, last }) => {
        const body = paras.map(p => formatRoleplayText(p, { hideStateBlocks: true })).join("<br><br>");
        const photo = first && m.img
          ? `<div class="rp-msg-photo-wrap"><img class="rp-msg-photo-img" src="${m.img}" alt="Photo"></div>`
          : "";
        const time = last ? m.time : "";
        if (m.isUser) {
          return `<div class="rp-msg-row user${first ? "" : " cont"}">
              ${time ? `<span class="rp-msg-timestamp-user">${time}</span>` : ""}
              <div class="rp-msg-bubble-user">${photo}${body}</div>
            </div>`;
        }
        return `<div class="rp-msg-row bot${first ? "" : " cont"}">
            <div class="rp-msg-avatar-col">
              <img class="rp-msg-avatar-img" src="${charAvatarUrl}" alt="${escapeHtml(charName)}">
              <span class="rp-msg-avatar-name">${escapeHtml(charName)}</span>
            </div>
            <div class="rp-msg-bubble-bot">${photo}${body}</div>
            ${time ? `<span class="rp-msg-timestamp-bot">${time}</span>` : ""}
          </div>`;
      };

      // Split text into paragraph units (and very long paragraphs into sentence groups).
      const splitUnits = (text) => {
        const units = [];
        String(text).split(/\n\s*\n|\n/).map(s => s.trim()).filter(Boolean).forEach(p => {
          if (p.length <= 520) { units.push(p); return; }
          const sentences = p.match(/[^.!?。！？]+[.!?。！？]+["”』」*)]*\s*|.+$/g) || [p];
          let buf = "";
          sentences.forEach(s => {
            if ((buf + s).length > 420 && buf) { units.push(buf.trim()); buf = ""; }
            buf += s;
          });
          if (buf.trim()) units.push(buf.trim());
        });
        return units.length ? units : [""];
      };

      let baseTime = new Date();
      baseTime.setHours(10, 14, 0, 0);
      const chatMessages = currentHistory.map((msg, idx) => {
        const msgTs = Number(msg.timestamp) ? new Date(msg.timestamp * 1000) : new Date(baseTime.getTime() + idx * 95000);
        const cleanContent = String(msg.content || "")
          .replace(/```(?:\{\{info\}\}|info)[\s\S]*?```/gi, "")
          .replace(/```+\s*(?:status|current[ _-]?situation|permanent[ _-]?memor(?:y|ies)|emotion|wardrobe)\b[\s\S]*?```+/gi, "")
          .replace(/(?:^|\n)(?:```+|`)\s*(?:status|current[ _-]?situation|permanent[ _-]?memor(?:y|ies)|emotion|wardrobe)\s*:?[\s\S]*$/gi, "")
          .replace(/\[OOC:[\s\S]*?\]/gi, "")
          .trim();
        return {
          isUser: msg.role === "user",
          time: `${String(msgTs.getHours()).padStart(2, "0")}:${String(msgTs.getMinutes()).padStart(2, "0")}`,
          img: msg.image_url || msg.user_image || "",
          units: splitUnits(cleanContent)
        };
      }).filter(m => m.img || m.units.some(u => u));

      // Off-screen sandbox page with the exact print geometry.
      try { if (document.fonts && document.fonts.ready) await document.fonts.ready; } catch (_) {}
      const sandbox = document.createElement("div");
      sandbox.className = "rp-print-sandbox";
      const sandboxPage = document.createElement("section");
      sandboxPage.className = "rp-print-page rp-chat-page";
      sandboxPage.innerHTML = buildChatPageHtml(2, 2, "");
      sandbox.appendChild(sandboxPage);
      document.body.appendChild(sandbox);
      const stream = sandboxPage.querySelector(".rp-chat-stream");
      const overflows = () => stream.scrollHeight > stream.clientHeight + 1;

      const chatChunks = [];
      let pageRows = [];
      const flushPage = () => {
        if (pageRows.length) chatChunks.push(pageRows);
        pageRows = [];
        stream.innerHTML = "";
      };
      const tryAppend = (html) => {
        const holder = document.createElement("div");
        holder.innerHTML = html.trim();
        const el = holder.firstElementChild;
        stream.appendChild(el);
        if (overflows()) { el.remove(); return false; }
        return true;
      };

      chatMessages.forEach(m => {
        let start = 0;
        let first = true;
        while (start < m.units.length) {
          // Find the largest run of units [start, end) that fits on the current page.
          let end = m.units.length;
          let fitted = false;
          while (end > start) {
            const html = buildRowHtml(m, m.units.slice(start, end), { first, last: end === m.units.length });
            if (tryAppend(html)) { pageRows.push(html); fitted = true; break; }
            end--;
          }
          if (fitted) { start = end; first = false; continue; }
          if (pageRows.length) { flushPage(); continue; } // retry on a fresh page
          // A single unit taller than an empty page: place it anyway (clipped safely).
          const html = buildRowHtml(m, [m.units[start]], { first, last: start + 1 === m.units.length });
          pageRows.push(html);
          flushPage();
          start += 1;
          first = false;
        }
      });
      flushPage();
      document.body.removeChild(sandbox);
      if (chatChunks.length === 0) chatChunks.push([]);

      const totalPages = 1 + chatChunks.length;

      // PAGE 1: CHARACTER CARD (PROFILE — A4)
      const cardPage = document.createElement("section");
      cardPage.className = "rp-print-page";
      cardPage.innerHTML = `
        <div class="rp-print-inner">
          ${floretSvg("tl")}${floretSvg("tr")}${floretSvg("bl")}${floretSvg("br")}
          <div class="rp-watermark-cathedral-header">${cathedralSvg("0.18")}</div>

          <!-- Header -->
          <header class="rp-print-header">
            <div class="rp-print-header-left">
              <h1 class="rp-print-main-title">Character Card</h1>
              <span class="rp-print-cross-star">✦</span>
            </div>
            <div class="rp-print-header-right">
              <div class="rp-print-app-logo">
                <span>RealmPlay</span>
                <span class="rp-print-app-logo-badge">ADV</span>
              </div>
            </div>
          </header>

          <div class="rp-print-divider">
            <span class="rp-print-divider-emblem">✦</span>
          </div>

          <!-- Character Heading Row & Metadata Table -->
          <div class="rp-char-top-block">
            <div class="rp-char-heading-row">
              <h2 class="rp-char-title">${escapeHtml(charName)}</h2>
              <span class="rp-char-v2">Character Profile</span>
            </div>

            <!-- Metadata Table: 5 fields in order [Name, Gender, Age, Personality, Status] -->
            <table class="rp-meta-table">
              <thead>
                <tr>
                  <th style="width: 20%;">Name</th>
                  <th style="width: 15%;">Gender</th>
                  <th style="width: 15%;">Age</th>
                  <th style="width: 33%;">Personality</th>
                  <th style="width: 17%;">Status</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td title="${escapeHtml(charName)}">${escapeHtml(charName)}</td>
                  <td title="${escapeHtml(charGender)}">${escapeHtml(charGender)}</td>
                  <td title="${escapeHtml(charAge)}">${escapeHtml(charAge)}</td>
                  <td title="${escapeHtml(charPersonality)}">${escapeHtml(charPersonality)}</td>
                  <td title="${escapeHtml(charStatus)}">${escapeHtml(charStatus)}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Middle Row: Portrait Image + Character Analysis & Background side by side -->
          <div class="rp-middle-grid">
            <!-- Left: Portrait Box (Clean, matched height) -->
            <div class="rp-portrait-box">
              <img class="rp-portrait-img" src="/api/characters/${encodeURIComponent(activeCharacter)}/avatar?print=${Date.now()}" alt="${escapeHtml(charName)}" onerror="this.src='/api/characters/${encodeURIComponent(activeCharacter)}/avatar'">
            </div>

            <!-- Right: Character Analysis & Background Details Column -->
            <div class="rp-details-col">
              <!-- Analysis -->
              <div class="rp-analysis-box">
                <div class="rp-analysis-title-row">
                  <span class="rp-analysis-title">Character Analysis</span>
                  <div class="rp-analysis-rule"></div>
                  <span class="rp-analysis-star">✦</span>
                </div>
                <div class="rp-token-stats">
                  <div class="rp-token-stat-item">
                    <strong>${Number(analysis.total_tokens || 2399).toLocaleString()}</strong>
                    <span>Card text tokens</span>
                  </div>
                  <div class="rp-token-stat-item">
                    <strong>${Number(analysis.summary_tokens || 223).toLocaleString()}</strong>
                    <span>Summary tokens</span>
                  </div>
                </div>

                <div class="rp-chart-grid">
                  <div class="rp-pie-donut" style="background:${pieGradient};"></div>
                  <div class="rp-chart-legend">
                    ${analysisParts.map((part, i) => `
                      <div class="rp-legend-row">
                        <i class="rp-legend-dot" style="background:${pieColors[i % pieColors.length]}"></i>
                        <span class="rp-legend-lbl">${escapeHtml(String(part.field || part.name || "").replace(/_/g, " "))}</span>
                        <strong class="rp-legend-val">${Number(part.percent || 0).toFixed(1)}%</strong>
                      </div>
                    `).join("")}
                  </div>
                </div>
              </div>

              <!-- Background Box -->
              <div class="rp-summary-card">
                <div class="rp-summary-head">
                  <span class="rp-summary-title">Background</span>
                  <span class="rp-summary-cross">♱</span>
                </div>
                <p class="rp-summary-desc">${escapeHtml(charBackground)}</p>
              </div>
            </div>
          </div>

          <!-- Bottom Description Section -->
          <div class="rp-desc-section">
            <div class="rp-desc-header">Description</div>
            <div class="rp-desc-body">${escapeHtml(descContextText)}</div>
          </div>

          <!-- Page 1 Footer -->
          <footer class="rp-page-footer">
            <div class="rp-page-footer-row">
              <span class="rp-page-no-indicator">PAGE 1 / ${totalPages}</span>
            </div>
          </footer>
        </div>
      `;

      printRoot.appendChild(cardPage);

      // PAGE 2+: PAGINATED CHAT HISTORY (CHAT — A4)
      chatChunks.forEach((rows, pageIdx) => {
        const chatPage = document.createElement("section");
        chatPage.className = "rp-print-page rp-chat-page";
        chatPage.innerHTML = buildChatPageHtml(pageIdx + 2, totalPages, rows.join(""));
        printRoot.appendChild(chatPage);
      });

      const allPrintImages = Array.from(printRoot.querySelectorAll("img"));
      await Promise.all(allPrintImages.map(img => img.decode ? img.decode().catch(() => {}) : Promise.resolve()));

      if (openDialog) {
        const prevTitle = document.title;
        document.title = `RealmPlay - ${charName}`;
        try {
          window.print();
        } finally {
          window.addEventListener("afterprint", () => {
            document.title = prevTitle;
          }, { once: true });
        }
      }
    }

    window.addEventListener("beforeprint", () => {
      const printRoot = document.getElementById("print-export");
      if (printRoot && printRoot.parentElement !== document.body) document.body.appendChild(printRoot);
    });
    window.addEventListener("keydown", (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "p") {
        event.preventDefault();
        printChatHistory();
      }
    }, true);

    // --- CHAT SEND & ACTIONS ---
    async function sendMessage(options = {}) {
      if (!activeCharacter) {
        alert("กรุณาPlease select a character firstเริ่มSend message");
        return;
      }

      const input = document.getElementById("chat-input");
      const text = input.value.trim();
      if (!text && !attachedVisionBase64) return;

      const imgPayload = attachedVisionBase64;
      const historyBeforeSend = currentHistory.slice();
      const manualWardrobe = options.manualWardrobe === true;
      input.value = "";
      clearVisionAttachment();

      // Manual wardrobe controls are character-side events. Do not display a
      // user message bubble for an action issued from the outfit panel.
      if (!manualWardrobe) {
        currentHistory.push({
          role: "user",
          content: text,
          user_image: imgPayload
        });
        renderChatHistory(currentHistory, true);
      }
      if (window.showRpGeneratingBubble) window.showRpGeneratingBubble();
      requestSmsNotificationPermission();

      try {
        const res = await fetch("/api/chat/send", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({
            character_name: activeCharacter,
            message: text,
            image_base64: imgPayload,
            manual_wardrobe: manualWardrobe
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || `Send messageไม่สำเร็จ (${res.status})`);
        renderChatHistory(data.history, true);
        await refreshChatInbox();
        if (!ttsAutoplayEnabled) playSmsDing();
        autoLoadLatestTTS(data.history);
        if (data.image_error) showNotice("สร้างภาพไม่สำเร็จ: " + data.image_error, "error");
        if (data.state) {
          applyResponseState(data.state);
        }
        if (data.reward_update) {
          updatePlayerRewardsUI(data.reward_update.profile);
          if (data.reward_update.leveled_up) {
            showNotice(`🎉 Level Up! เลเวลของคุณเพิ่มขึ้นเป็น LV.${data.reward_update.new_level}! (+Stat & Skill Points)`);
          }
        }
        if (data.trigger_image) {
          const targetIndex = (data.message_index !== undefined && data.message_index !== null) ? data.message_index : (currentHistory.length - 1);
          generateContextImage(targetIndex);
        }
      } catch (e) {
        console.error("sendMessage error:", e);
        // The server rejects messages while the character sleeps, so do not
        // leave an unsaved optimistic user bubble in the visible history.
        currentHistory = historyBeforeSend;
        renderChatHistory(currentHistory, true);
        const message = e.message || "ส่งข้อความไม่สำเร็จ";
        if (message.includes("กำลังหลับอยู่")) {
          showNotice(message, "info");
        } else {
          alert("Send messageไม่สำเร็จ: " + message);
        }
      }
    }

    function handleInputKey(e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    }

    function handleVisionFileSelect(e) {
      const file = e.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (evt) => {
        attachedVisionBase64 = evt.target.result;
        document.getElementById("vision-preview-img").src = attachedVisionBase64;
        document.getElementById("vision-preview-floating").style.display = "flex";
      };
      reader.readAsDataURL(file);
    }

    function clearVisionAttachment() {
      attachedVisionBase64 = null;
      document.getElementById("vision-preview-floating").style.display = "none";
      document.getElementById("vision-file-input").value = "";
    }

    async function regenerateReply(idx, promptOverride = "") {
      if (!activeCharacter) return;
      if (window.showRpGeneratingBubble) window.showRpGeneratingBubble();
      try {
        const res = await fetch("/api/chat/regenerate", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({
            character_name: activeCharacter,
            message_index: idx
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Request failed");
        const targetIndex = (data.index !== undefined && data.index !== null) ? data.index : idx;
        messageAudioCache.delete(targetIndex);
        renderChatHistory(data.history, false);
        await refreshChatInbox();
        autoLoadLatestTTS(data.history);
        if (data.state) {
          applyResponseState(data.state);
        }
        if (data.trigger_image || promptOverride) {
          generateContextImage(targetIndex, null, promptOverride || "");
        }
      } catch (e) {
        console.error("regenerate error:", e);
        showNotice("Regenerate ไม่สำเร็จ: " + e.message, "error");
      }
    }

    // Image Generation Cancellation Map
    const activeImageAbortControllers = new Map();

    async function stopImageGeneration(idx) {
      // 1. Abort client-side fetch if exists
      if (idx !== undefined && idx !== null && activeImageAbortControllers.has(idx)) {
        try { activeImageAbortControllers.get(idx).abort(); } catch (_) {}
        activeImageAbortControllers.delete(idx);
      } else {
        activeImageAbortControllers.forEach(ctrl => {
          try { ctrl.abort(); } catch (_) {}
        });
        activeImageAbortControllers.clear();
      }

      // 2. Call server to interrupt ComfyUI execution & cancel task
      try {
        await fetch("/api/image/stop", {
          method: "POST",
          headers: { "Authorization": `Bearer ${token}` }
        });
      } catch (err) {
        console.warn("Call to /api/image/stop failed:", err);
      }

      // 3. Clear generating_image flag on history
      if (idx !== undefined && idx !== null && currentHistory[idx]) {
        delete currentHistory[idx].generating_image;
        renderChatHistory(currentHistory, false);
      } else {
        currentHistory.forEach(m => {
          if (m.generating_image) delete m.generating_image;
        });
        renderChatHistory(currentHistory, false);
      }

      showNotice("ยกเลิกและหยุดการสร้างภาพแล้ว (Stopped image gen)");
    }

    function positivePromptFromStoredPrompt(value) {
      const stored = String(value || "").trim();
      const match = stored.match(/(?:^|\n\n)POSITIVE:\s*\n([\s\S]*?)(?=\n\n(?:EMOTION|SUFFIX|NEGATIVE):|$)/i);
      return (match ? match[1] : stored).trim();
    }

    function openRegeneratePromptOptions(idx) {
      // Edit/reuse previous IMAGE prompt only — same pipeline as bubble Generate.
      // Must NOT call regenerateReply (that rewrites dialogue via /api/chat/regenerate).
      const previous = positivePromptFromStoredPrompt(currentHistory[idx]?.image_prompt);
      if (!previous) { showNotice("ไม่มี prompt ภาพเดิมสำหรับข้อความนี้", "error"); return; }
      const content = rpDialog("แก้ prompt ภาพแล้วสร้างรูปใหม่");
      content.innerHTML = "<p>ใช้ Positive prompt เดิม หรือแก้ไข แล้วสร้างรูปใหม่แทนที่ภาพนี้เท่านั้น — ไม่แก้ข้อความในแชท</p>";
      const input = document.createElement("textarea");
      input.className = "form-input"; input.rows = 8; input.maxLength = 6000; input.value = previous;
      content.append(input);
      const actions = document.createElement("div"); actions.className = "rp-card-actions";
      const usePrevious = rpCardButton("ใช้ prompt เดิม", () => {
        document.getElementById("rp-dialog").close();
        generateContextImage(idx, null, previous);
      });
      const useEdited = rpCardButton("ใช้ prompt ที่แก้แล้ว (เฉพาะรูป)", () => {
        const edited = input.value.trim();
        if (!edited) { showNotice("Prompt ต้องไม่ว่าง", "error"); return; }
        document.getElementById("rp-dialog").close();
        generateContextImage(idx, null, edited);
      });
      const regenBoth = rpCardButton("Regen ข้อความ + รูปด้วย prompt นี้", () => {
        const edited = input.value.trim();
        if (!edited) { showNotice("Prompt ต้องไม่ว่าง", "error"); return; }
        document.getElementById("rp-dialog").close();
        regenerateReply(idx, edited);
      });
      actions.append(usePrevious, useEdited, regenBoth); content.append(actions); input.focus();
    }

    async function generateContextImage(idx, button, promptOverride = "") {
      if (!activeCharacter) return;
      const characterName = activeCharacter;
      // A second manual click is a new visual interpretation of this same
      // turn.  The server asks for a fresh seed, while the canonical turn
      // state remains fixed for continuity.
      const refreshPromptSeed = !promptOverride && Boolean(currentHistory[idx]?.image_prompt);
      const originalLabel = button?.innerHTML;
      if (button) { button.disabled = true; button.textContent = "⏳"; }
      if (currentHistory[idx]) {
        currentHistory[idx].generating_image = true;
        renderChatHistory(currentHistory, false);
      }

      const abortController = new AbortController();
      activeImageAbortControllers.set(idx, abortController);

      try {
        const res = await fetch("/api/chat/generate_context_image", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          signal: abortController.signal,
          body: JSON.stringify({
            character_name: characterName,
            message_index: idx,
            prompt_override: promptOverride || null,
            refresh_prompt_seed: refreshPromptSeed
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || `สร้างภาพไม่สำเร็จ (${res.status})`);
        if (!data.image_url) throw new Error("ComfyUI ไม่ส่งรูปภาพกลับมา");
        const resolvedIdx = (data.message_index !== undefined && data.message_index !== null && currentHistory[data.message_index]) ? data.message_index : idx;
        if (Array.isArray(data.history) && data.history.length) {
          currentHistory = data.history;
        }
        if (currentHistory[resolvedIdx]) {
          currentHistory[resolvedIdx].image_url = data.image_url;
          currentHistory[resolvedIdx].image_prompt = data.prompt_used || "";
          if (activeCharacter === characterName) {
            const sprites = characters.find(c => c.name === characterName)?.sprites || [];
            await loadCharacterGallery(characterName, sprites);
          }
        }
      } catch (e) {
        if (e.name === "AbortError") {
          console.log("Context image generation aborted by user.");
        } else {
          showNotice("ไม่สามารถสร้างภาพได้: " + e.message, "error");
        }
      } finally {
        activeImageAbortControllers.delete(idx);
        if (currentHistory[idx]) {
          delete currentHistory[idx].generating_image;
          renderChatHistory(currentHistory, false);
        }
        if (button?.isConnected) { button.disabled = false; button.innerHTML = originalLabel; }
      }
    }

    async function previewContextImagePrompt(button) {
      if (!activeCharacter || !currentHistory.length) { showNotice("เลือกตัวละครและเปิดบทสนทนาก่อน", "error"); return; }
      const original = button?.innerHTML;
      if (button) { button.disabled = true; button.textContent = "⏳"; }
      try {
        const res = await fetch("/api/chat/image-intent-preview", {method:"POST", headers:{"Content-Type":"application/json", "Authorization":`Bearer ${token}`}, body:JSON.stringify({character_name:activeCharacter, message_index:currentHistory.length - 1})});
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "ตรวจสอบ prompt ไม่สำเร็จ");
        const prompt = document.getElementById("rail-image-prompt");
        if (prompt) prompt.value = data.positive_prompt || "";
        showNotice("แสดง prompt จากบริบทล่าสุดแล้ว — ยังไม่ได้สั่งสร้างภาพ", "success");
      } catch (e) { showNotice("Preview ไม่สำเร็จ: " + e.message, "error"); }
      finally { if (button?.isConnected) { button.disabled = false; button.innerHTML = original; } }
    }

    async function generateMessageTTS(idx, { button = null, autoplay = true, quiet = false } = {}) {
      const msg = currentHistory[idx];
      if (!msg) return;
      const original = button?.innerHTML;
      if (button) { button.disabled = true; button.textContent = "⏳"; }
      const controller = new AbortController();
      activeTtsController?.abort();
      activeTtsController = controller;
      try {
        const voice = document.getElementById("rail-voice-tts")?.value || "th-TH-PremwadeeNeural";
        const rateVal = parseInt(document.getElementById("rail-voice-rate")?.value || 0);
        const rateStr = (rateVal >= 0 ? `+${rateVal}%` : `${rateVal}%`);
        const rvcOn = document.getElementById("rail-voice-rvc-check")?.checked || false;
        const rvcModel = document.getElementById("rail-voice-rvc-model")?.value || "";
        const rvcIndex = document.getElementById("rail-voice-rvc-index")?.value || "";
        const pitch = parseInt(document.getElementById("rail-voice-pitch")?.value || 0);
        const indexRate = parseFloat(document.getElementById("rail-voice-index-rate")?.value || 0.75);
        const protect = parseFloat(document.getElementById("rail-voice-protect")?.value || 0.33);

        const res = await fetch("/api/voice/speak", {
          method: "POST",
          signal: controller.signal,
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({
            text: msg.content,
            voice: voice,
            rate: rateStr,
            pitch: pitch,
            rvc_model: (rvcOn && rvcModel) ? rvcModel : null,
            rvc_index: rvcOn ? rvcIndex : null,
            rvc_index_rate: rvcOn ? indexRate : null,
            rvc_protect: rvcOn ? protect : null
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "สร้างเสียงไม่สำเร็จ");
        if (data.audio_url) {
          messageAudioCache.set(idx, data.audio_url);
          if (autoplay) {
            const audio = new Audio(data.audio_url);
            activeTtsAudio?.pause();
            activeTtsAudio = audio;
            audio.addEventListener("ended",()=>{if(activeTtsAudio===audio)activeTtsAudio=null;},{once:true});
            await audio.play();
          }
          if (!quiet) showNotice(autoplay ? "สร้างและเล่นเสียงแล้ว" : "สร้างเสียงอัตโนมัติแล้ว", "success");
        } else {
          throw new Error("เซิร์ฟเวอร์ไม่ส่งไฟล์เสียงกลับมา");
        }
      } catch (e) {
        if (e.name === "AbortError") return;
        console.error("bubble TTS error:", e);
        if (!quiet) showNotice("สร้างเสียงไม่สำเร็จ: " + e.message, "error");
      } finally {
        if (activeTtsController === controller) activeTtsController = null;
        if (button?.isConnected) { button.disabled = false; button.innerHTML = original; }
      }
    }

    function playTTS(idx, button) {
      return generateMessageTTS(idx, { button, autoplay:true, quiet:false });
    }

    function autoLoadLatestTTS(history) {
      if (!ttsAutoloadEnabled || !Array.isArray(history)) return;
      let idx = history.length - 1;
      while (idx >= 0 && history[idx]?.role !== "assistant") idx--;
      if (idx < 0 || messageAudioCache.has(idx)) return;
      generateMessageTTS(idx, { autoplay:ttsAutoplayEnabled, quiet:!ttsAutoplayEnabled });
    }

    function replayTTS(idx) {
      const url=messageAudioCache.get(idx); if(!url){showNotice("ยังไม่มีเสียงที่สร้างไว้ กด 🔊 ก่อน","error");return;}
      new Audio(url).play().catch(e=>showNotice("เล่นเสียงไม่สำเร็จ: "+e.message,"error"));
    }
    async function continueReply(idx,button){
      const old=button?.innerHTML;if(button){button.disabled=true;button.textContent="⏳";}
      if(window.showRpGeneratingBubble) window.showRpGeneratingBubble();
      try{const res=await fetch("/api/chat/continue",{method:"POST",headers:{"Content-Type":"application/json","Authorization":"Bearer "+token},body:JSON.stringify({character_name:activeCharacter,message_index:idx})});const data=await res.json();if(!res.ok)throw new Error(data.detail||"เขียนต่อไม่สำเร็จ");renderChatHistory(data.history,true);await refreshChatInbox();autoLoadLatestTTS(data.history);if(data.state)applyResponseState(data.state);}catch(e){showNotice(e.message,"error");}finally{if(button?.isConnected){button.disabled=false;button.innerHTML=old;}}
    }
    function toggleMessageSelectionMode(){messageSelectionMode?exitMessageSelection():startMessageSelection();}
    function startMessageSelection(){if(!activeCharacter){showNotice("Please select a character first","error");return;}messageSelectionMode=true;selectedMessageIndices.clear();document.getElementById("multi-delete-bar").classList.add("active");const toggle=document.getElementById("message-select-toggle");toggle?.classList.add("active");toggle?.setAttribute("aria-pressed","true");updateSelectionCount();renderChatHistory(currentHistory,false);}
    function exitMessageSelection(){messageSelectionMode=false;selectedMessageIndices.clear();document.getElementById("multi-delete-bar").classList.remove("active");const toggle=document.getElementById("message-select-toggle");toggle?.classList.remove("active");toggle?.setAttribute("aria-pressed","false");renderChatHistory(currentHistory,false);}
    function toggleMessageSelection(i,on){on?selectedMessageIndices.add(i):selectedMessageIndices.delete(i);updateSelectionCount();const row=document.getElementById(`msg-row-${i}`);row?.classList.toggle("message-selected",on);const checkbox=row?.querySelector(".msg-select-box");if(checkbox)checkbox.checked=on;}
    function updateSelectionCount(){const count=selectedMessageIndices.size,total=currentHistory.length;document.getElementById("multi-delete-count").textContent=`เลือก ${count} ข้อความ`;const del=document.getElementById("delete-selected-messages-button");if(del)del.disabled=count===0;const all=document.getElementById("select-all-messages-button");if(all)all.textContent=total>0&&count===total?"☐ ยกเลิกทั้งหมด":"☑ ทั้งหมด";}
    function toggleSelectAllMessages(){if(selectedMessageIndices.size===currentHistory.length)selectedMessageIndices.clear();else currentHistory.forEach((_,i)=>selectedMessageIndices.add(i));updateSelectionCount();renderChatHistory(currentHistory,false);}
    async function deleteSelectedMessages(){const indices=[...selectedMessageIndices];if(!indices.length)return;if(!await openConfirmDialog(`ลบ ${indices.length} ข้อความที่เลือกนี้หรือไม่?`,"ยืนยันการลบหลายข้อความ"))return;try{const res=await fetch("/api/chat/delete_messages",{method:"POST",headers:{"Content-Type":"application/json","Authorization":"Bearer "+token},body:JSON.stringify({character_name:activeCharacter,indices:indices})});const data=await res.json();if(!res.ok)throw new Error(data.detail||"Failed to delete");currentHistory=data.history;if(data.state)applyResponseState(data.state);exitMessageSelection();}catch(e){showNotice(e.message,"error");}}

    function closeChatManager(){document.getElementById("chat-manager-modal").style.display="none";}
    async function openChatManager(){if(!activeCharacter){showNotice("Please select a character first","error");return;}document.getElementById("chat-manager-modal").style.display="flex";await loadChatSessions();}
    function populateSessionSource(sessions){const select=document.getElementById("new-session-source");if(!select)return;const selected=select.value||"default";select.innerHTML='<option value="default">Fresh from character default</option>';(sessions||[]).forEach(session=>{const option=document.createElement("option");option.value=session.id;option.textContent=`Continue from: ${session.title||"Untitled chat"}`;select.appendChild(option);});select.value=[...select.options].some(option=>option.value===selected)?selected:"default";}
    async function loadChatSessions(){const box=document.getElementById("chat-session-list");box.textContent="กำลังโหลด...";try{const res=await fetch("/api/characters/"+encodeURIComponent(activeCharacter)+"/chat-sessions",{headers:{"Authorization":"Bearer "+token}});const data=await res.json();if(!res.ok)throw new Error(data.detail||"Failed to load");populateSessionSource(data.sessions||[]);box.innerHTML="";(data.sessions||[]).forEach(x=>{const row=document.createElement("div");row.className="session-row "+(x.id===data.active_id?"active":"");const info=document.createElement("div");info.innerHTML="<strong>"+escapeHtml(x.title)+"</strong><div style='font-size:11px;color:var(--text-muted)'>"+(x.message_count||0)+" ข้อความ</div>";const open=document.createElement("button");open.className="msg-act-btn";open.textContent="▶";open.title="Open chat";open.disabled=x.id===data.active_id;open.onclick=()=>activateChatSession(x.id);const del=document.createElement("button");del.className="msg-act-btn";del.textContent="🗑️";del.title="Delete chat";del.disabled=x.id===data.active_id;del.onclick=()=>deleteChatSession(x.id);row.append(info,open,del);box.appendChild(row);});}catch(e){box.textContent=e.message;}}
    async function createChatSession() {
      const name = activeCharacter;
      const title = document.getElementById("new-session-title").value.trim();
      const source_session_id = document.getElementById("new-session-source").value;
      const copy_history = !!document.getElementById("new-session-copy-history").checked;
      const res = await fetch("/api/characters/" + encodeURIComponent(name) + "/chat-sessions", {
        method: "POST", headers: {"Content-Type": "application/json", "Authorization": "Bearer " + token},
        body: JSON.stringify({title, source_session_id, copy_history})
      });
      const data = await res.json();
      if (!res.ok) { showNotice(data.detail || "Failed to create", "error"); return; }
      if (activeCharacter !== name) return;
      await selectCharacter(name);
      document.getElementById("new-session-title").value = "";
      if (activeCharacter === name) await loadChatSessions();
    }
    async function activateChatSession(id) {
      const name = activeCharacter;
      const res = await fetch("/api/characters/" + encodeURIComponent(name) + "/chat-sessions/" + id + "/activate", {
        method: "POST", headers: {"Authorization": "Bearer " + token}
      });
      const data = await res.json();
      if (!res.ok) { showNotice(data.detail || "Failed to open", "error"); return; }
      if (activeCharacter !== name) return;
      await selectCharacter(name);
      if (activeCharacter === name) closeChatManager();
    }
    async function deleteChatSession(id){if(!await openConfirmDialog("Delete chatนี้ถาวรหรือไม่? การกระทำนี้ไม่สามารถย้อนกลับได้","Confirm Delete Chat"))return;const res=await fetch("/api/characters/"+encodeURIComponent(activeCharacter)+"/chat-sessions/"+id,{method:"DELETE",headers:{"Authorization":"Bearer "+token}});const data=await res.json();if(!res.ok){showNotice(data.detail||"Failed to delete","error");return;}await loadChatSessions();}

    function closeContextUsage(){document.getElementById("context-usage-modal").style.display="none";}
    async function openContextUsage(){if(!activeCharacter){showNotice("Please select a character first","error");return;}const modal=document.getElementById("context-usage-modal"),box=document.getElementById("context-usage-content");modal.style.display="flex";box.textContent="Loading data...";try{const res=await fetch("/api/chat/context_usage?character_name="+encodeURIComponent(activeCharacter),{headers:{"Authorization":"Bearer "+token}});const data=await res.json();if(!res.ok)throw new Error(data.detail||"Failed to load");const colors=["#8b5cf6","#38bdf8","#34d399","#f59e0b","#f472b6","#64748b"];let cursor=0;const stops=data.parts.map((x,i)=>{const a=cursor;cursor+=x.percent;return colors[i%colors.length]+" "+a+"% "+cursor+"%";}).join(",");box.innerHTML='<div class="token-summary"><div class="token-pie" style="background:conic-gradient('+(stops||'#334155 0 100%')+')"><div class="token-pie-center"><strong>'+data.total+'</strong><span>'+data.context_percent+'% context</span></div></div><div>'+data.parts.map((x,i)=>'<div class="token-part"><i class="token-swatch" style="background:'+colors[i%colors.length]+'"></i><span>'+escapeHtml(x.name)+'</span><strong>'+x.tokens+' · '+x.percent+'%</strong></div>').join('')+'<div style="margin-top:8px;font-size:12px;color:var(--text-muted)">Context limit '+Number(data.context_limit).toLocaleString()+' tokens</div></div></div>';}catch(e){box.textContent=e.message;}}

    function openEditMessage(idx) {
      const textDiv = document.getElementById(`msg-text-${idx}`);
      const editBox = document.getElementById(`msg-edit-box-${idx}`);
      const editInput = document.getElementById(`msg-edit-input-${idx}`);
      if (!textDiv || !editBox || !editInput) return;

      const bubble = textDiv.closest('.msg-bubble');
      if (bubble) {
        const bounds = bubble.getBoundingClientRect();
        // Keep a usable editor width even when the original message is very short.
        const minEditorWidth = Math.min(440, Math.floor(window.innerWidth * (window.innerWidth <= 720 ? 0.76 : 0.45)));
        bubble.style.width = `${Math.max(Math.ceil(bounds.width), minEditorWidth)}px`;
        bubble.style.maxWidth = '100%';
        bubble.style.minHeight = `${Math.ceil(bounds.height)}px`;
      }
      const textHeight = textDiv.getBoundingClientRect().height;
      textDiv.style.display = "none";
      editBox.style.display = "block";
      editInput.value = currentHistory[idx].content;
      editInput.style.height = `${Math.min(Math.max(Math.ceil(textHeight), 80), Math.round(window.innerHeight * 0.5))}px`;
      editInput.focus();
    }

    function handleEditMessageKey(e, idx) {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        saveEditMessage(idx);
      } else if (e.key === "Escape") {
        e.preventDefault();
        cancelEditMessage(idx);
      }
    }

    function cancelEditMessage(idx) {
      const textDiv = document.getElementById(`msg-text-${idx}`);
      const editBox = document.getElementById(`msg-edit-box-${idx}`);
      const bubble = textDiv?.closest('.msg-bubble');
      if (textDiv) textDiv.style.display = "block";
      if (editBox) editBox.style.display = "none";
      if (bubble) {
        bubble.style.width = '';
        bubble.style.maxWidth = '';
        bubble.style.minHeight = '';
      }
    }

    function applyResponseState(state) {
      if (!state) return;
      if (state.scenario !== undefined && document.getElementById("pane-input-situation")) {
        setSituationPane(state.scenario || "");
      }
      if (state.status !== undefined && document.getElementById("pane-input-status")) {
        document.getElementById("pane-input-status").value = statusWithMood(state.status, state.emotion);
      }
      if (state.scene_state !== undefined && typeof renderHModeGauge === "function") {
        renderHModeGauge(state.scene_state);
      }
      if (state.memory !== undefined && document.getElementById("pane-input-memory")) {
        document.getElementById("pane-input-memory").value = state.memory || "";
      }
      if (state.outfits && typeof state.outfits === "object") {
        currentWardrobe = state.outfits;
        if (typeof renderOutfits3x4Grid === "function") renderOutfits3x4Grid(currentWardrobe);
      }
      if (Array.isArray(state.inventory) && typeof renderInventoryList === "function") {
        currentInventory = state.inventory;
        renderInventoryList(currentInventory);
      }
    }

async function saveEditMessage(idx) {
      const editInput = document.getElementById(`msg-edit-input-${idx}`);
      const newText = editInput.value.trim();
      try {
        const res = await fetch("/api/chat/edit", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({
            character_name: activeCharacter,
            index: idx,
            content: newText
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Request failed");
        if (!res.ok) throw new Error(data.detail || "Request failed");
        renderChatHistory(data.history, false);
        if (data.state) applyResponseState(data.state);
      } catch (e) {
        alert("แก้ไขไม่สำเร็จ: " + e.message);
      }
    }

    async function deleteMessage(idx) {
      if (!await openConfirmDialog("คุณแน่ใจว่าต้องการลบข้อความนี้?", "ยืนยันการลบข้อความ")) return;
      try {
        const res = await fetch("/api/chat/delete_message", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({
            character_name: activeCharacter,
            index: idx
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Request failed");
        renderChatHistory(data.history, false);
        if (data.state) applyResponseState(data.state);
      } catch (e) {
        showNotice("Failed to delete: " + e.message, "error");
      }
    }

    async function deleteMessageImage(idx, imgUrl) {
      if (!await openConfirmDialog("ต้องการลบรูปภาพนี้ออกจากข้อความใช่หรือไม่?", "ยืนยันการลบรูปภาพ")) return;
      try {
        await fetch("/api/chat/delete_image", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({
            character_name: activeCharacter,
            message_index: idx,
            image_url: imgUrl
          })
        });
        delete currentHistory[idx].image_url;
        renderChatHistory(currentHistory, false);
      } catch (e) {}
    }

    // --- CARD IMPORT (BUTTON ONLY - NO DRAG & DROP) & EXPORT ---
    async function uploadCharacterCard(e) {
      const file = e.target.files[0];
      if (!file) return;
      if (!/\.(png|json)$/i.test(file.name)) {
        alert("กรุณาเลือก Character Card แบบ .png หรือ .json");
        return;
      }

      const formData = new FormData();
      formData.append("file", file);

      try {
        const res = await fetch("/api/characters/import_png", {
          method: "POST",
          headers: { "Authorization": `Bearer ${token}` },
          body: formData
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "นำเข้าการ์ดล้มเหลว");
        alert(`🎉 นำเข้า Character Card V2 สำเร็จ!\nชื่อ: ${data.name}\nสกัด Sprites อารมณ์ได้: ${data.extracted_sprites_count} ภาพ`);
        await loadCharacters();
        selectCharacter(data.name);
      } catch (err) {
        alert(`❌ ไม่สามารถนำเข้าการ์ดได้: ${err.message}`);
      }
    }

    function exportCurrentCharPNG() {
      if (!activeCharacter) {
        alert("กรุณาPlease select a character firstส่งออกการ์ด");
        return;
      }
      window.location.href = `/api/characters/${encodeURIComponent(activeCharacter)}/export`;
    }

    // --- RANDOM CHARACTER GENERATOR ---
    let randomCharacterTheme = "fantasy";
    let cachedWardrobeCatalog = null;

    async function loadWardrobeCatalogForModal() {
      if (cachedWardrobeCatalog) return cachedWardrobeCatalog;
      try {
        const res = await fetch("/api/wardrobe/catalog", {
          headers: { "Authorization": `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          cachedWardrobeCatalog = data.slots || {};
          populateRandomOutfitDropdowns();
        }
      } catch (e) {
        console.warn("Failed to load wardrobe catalog for random character:", e);
      }
      return cachedWardrobeCatalog;
    }

    function populateRandomOutfitDropdowns() {
      if (!cachedWardrobeCatalog) return;
      const slotMap = {
        "rnd-slot-outer": "outer",
        "rnd-slot-top": "top",
        "rnd-slot-bottom": "bottom",
        "rnd-slot-socks": "socks",
        "rnd-slot-shoes": "shoes",
        "rnd-slot-neck_acc": "neck_acc"
      };

      for (const [elId, slot] of Object.entries(slotMap)) {
        const select = document.getElementById(elId);
        if (!select) continue;
        const currentVal = select.value;
        const items = cachedWardrobeCatalog[slot] || [];
        
        // Preserve first default option
        select.innerHTML = `<option value="">(🎲 Auto Random ${slot})</option>`;
        
        // Filter items that match selected theme loosely or list popular ones
        items.forEach(it => {
          const opt = document.createElement("option");
          opt.value = it.name || it.prompt;
          opt.textContent = `${it.name}${it.category ? ' [' + it.category + ']' : ''}`;
          select.appendChild(opt);
        });
        select.value = currentVal;
      }
    }

    function toggleRandomOutfitCustomizer() {
      const body = document.getElementById("random-outfit-customizer-body");
      const icon = document.getElementById("random-outfit-toggle-icon");
      if (!body) return;
      const isHidden = body.style.display === "none";
      body.style.display = isHidden ? "block" : "none";
      if (icon) icon.textContent = isHidden ? "▲ Hide Items" : "▼ Show Items";
      if (isHidden && !cachedWardrobeCatalog) {
        loadWardrobeCatalogForModal();
      }
    }

    function resetRandomOutfitDropdowns() {
      ["rnd-slot-outer", "rnd-slot-top", "rnd-slot-bottom", "rnd-slot-socks", "rnd-slot-shoes", "rnd-slot-neck_acc"].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = "";
      });
    }

    function triggerRandomCharacter() {
      randomCharacterTheme = "fantasy";
      document.getElementById("random-character-age").value = "";
      selectRandomTheme("fantasy");
      resetRandomOutfitDropdowns();
      loadWardrobeCatalogForModal();
      document.getElementById("random-character-modal").style.display = "flex";
    }
    function closeRandomCharacterModal() {
      document.getElementById("random-character-modal").style.display = "none";
    }
    function closeRandomCharacterModalOnBackdrop(event) {
      if (event.target === event.currentTarget) closeRandomCharacterModal();
    }
    function selectRandomTheme(theme) {
      randomCharacterTheme = theme;
      document.querySelectorAll("[data-random-theme]").forEach(el => el.classList.toggle("active", el.dataset.randomTheme === theme));
    }
    async function createRandomCharacter() {
      const btn = document.getElementById("btn-random-character-create");
      const sidebarBtn = document.getElementById("btn-random-char");
      const ageInput = document.getElementById("random-character-age").value.trim();
      let age = null;
      if (ageInput) {
        const parsed = Number(ageInput);
        age = Number.isFinite(parsed) ? parsed : ageInput;
      }

      // Collect user-selected wardrobe overrides
      const outfit_overrides = {};
      const slotMap = {
        "outer": "rnd-slot-outer",
        "top": "rnd-slot-top",
        "bottom": "rnd-slot-bottom",
        "socks": "rnd-slot-socks",
        "shoes": "rnd-slot-shoes",
        "neck_acc": "rnd-slot-neck_acc"
      };
      for (const [slot, elId] of Object.entries(slotMap)) {
        const val = document.getElementById(elId)?.value?.trim();
        if (val) outfit_overrides[slot] = val;
      }

      const originalText = btn.innerHTML;
      btn.disabled = true;
      if (sidebarBtn) sidebarBtn.disabled = true;
      btn.innerHTML = "⏳ Creating...";
      try {
        const res = await fetch("/api/characters/random-generate", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({
            gender: "female", theme: randomCharacterTheme, generate_avatar: true,
            age_mode: age === null ? "auto" : "custom",
            age,
            outfit_overrides: Object.keys(outfit_overrides).length > 0 ? outfit_overrides : null
          })
        });
        const result = await res.json();
        if (!res.ok || !result.ok) {
          throw new Error(result.detail || result.error || "สร้างตัวละครไม่สำเร็จ");
        }
        const avatarReady = result.avatar?.generated === true;
        const successMessage = avatarReady
          ? `🎲 สุ่มสร้างตัวละคร "${result.character.display_name}" พร้อมภาพการ์ดแล้ว!`
          : `🎲 สุ่มสร้างตัวละคร "${result.character.display_name}" แล้ว แต่ยังสร้างภาพการ์ดไม่สำเร็จ`;
        if (typeof showNotice === "function") {
          showNotice(successMessage, avatarReady ? "success" : "warning");
        } else {
          alert(successMessage + (result.avatar?.error ? `\n${result.avatar.error}` : ""));
        }
        await loadCharacters();
        if (result.character?.character_name) {
          selectCharacter(result.character.character_name);
        }
        closeRandomCharacterModal();
      } catch (err) {
        console.error("Random character error:", err);
        if (typeof showNotice === "function") {
          showNotice("เกิดข้อErrorในการสุ่มสร้างตัวละคร: " + err.message, "error");
        } else {
          alert("เกิดข้อErrorในการสุ่มสร้างตัวละคร: " + err.message);
        }
      } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
        if (sidebarBtn) sidebarBtn.disabled = false;
      }
    }

    // --- CHARACTER CREATE MODAL ---
    function toggleCreateCharOutfitCustomizer() {
      const body = document.getElementById("create-char-outfit-customizer-body");
      const icon = document.getElementById("create-char-outfit-toggle-icon");
      if (!body) return;
      const isHidden = body.style.display === "none";
      body.style.display = isHidden ? "block" : "none";
      if (icon) icon.textContent = isHidden ? "▲ Hide Items" : "▼ Show Items";
      if (isHidden) {
        populateCreateCharOutfitDropdowns();
      }
    }

    function resetCreateOutfitDropdowns() {
      ["create-slot-outer", "create-slot-top", "create-slot-bottom", "create-slot-socks", "create-slot-shoes", "create-slot-neck_acc"].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = "";
      });
    }

    async function populateCreateCharOutfitDropdowns() {
      const catalog = cachedWardrobeCatalog || await loadWardrobeCatalogForModal();
      if (!catalog) return;
      const slotMap = {
        "create-slot-outer": "outer",
        "create-slot-top": "top",
        "create-slot-bottom": "bottom",
        "create-slot-socks": "socks",
        "create-slot-shoes": "shoes",
        "create-slot-neck_acc": "neck_acc"
      };
      for (const [elId, slot] of Object.entries(slotMap)) {
        const select = document.getElementById(elId);
        if (!select) continue;
        const currentVal = select.value;
        const items = catalog[slot] || [];
        const isOpt = (slot === "outer" || slot === "neck_acc");
        select.innerHTML = `<option value="">(${isOpt ? "ไม่มี / ไม่สวม" : "ค่าเริ่มต้น / Auto " + slot})</option>`;
        items.forEach(it => {
          const opt = document.createElement("option");
          opt.value = it.prompt || it.name;
          opt.textContent = `${it.name}${it.category ? ' [' + it.category + ']' : ''}`;
          select.appendChild(opt);
        });
        select.value = currentVal;
      }
    }

    function openCharCreateModal() {
      newCharAvatarBase64 = null;
      document.getElementById("new-char-name").value = "";
      document.getElementById("new-char-firstmes").value = "";
      document.getElementById("new-char-personality").value = "";
      document.getElementById("new-char-persona").value = "";
      document.getElementById("new-char-avatar-preview").src = "https://api.dicebear.com/7.x/bottts/svg?seed=" + Date.now();
      resetCreateOutfitDropdowns();
      populateCreateCharOutfitDropdowns();
      document.getElementById("char-create-modal").style.display = "flex";
    }
    function closeCharCreateModal() {
      document.getElementById("char-create-modal").style.display = "none";
    }
    function closeCharCreateModalOnBackdrop(e) {
      if (e.target.id === "char-create-modal") closeCharCreateModal();
    }
    function handleNewCharAvatarSelect(e) {
      const file = e.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (evt) => {
        newCharAvatarBase64 = evt.target.result;
        document.getElementById("new-char-avatar-preview").src = newCharAvatarBase64;
      };
      reader.readAsDataURL(file);
    }
    async function saveCharCreateModal() {
      const name = document.getElementById("new-char-name").value.trim();
      if (!name) { alert("กรุณาระบุชื่อตัวละคร"); return; }
      const firstMes = document.getElementById("new-char-firstmes").value;
      const personality = document.getElementById("new-char-personality").value;
      const persona = document.getElementById("new-char-persona").value;
      const gender = document.getElementById("new-char-gender") ? document.getElementById("new-char-gender").value : "Female";
      const age = document.getElementById("new-char-age") ? document.getElementById("new-char-age").value : "";
      const status = document.getElementById("new-char-status") ? document.getElementById("new-char-status").value : "Single";
      const roleGoals = document.getElementById("new-char-role-goals") ? document.getElementById("new-char-role-goals").value : "";
      const sexPreference = document.getElementById("new-char-sex-preference") ? document.getElementById("new-char-sex-preference").value : "";
      const likesDislikes = document.getElementById("new-char-likes-dislikes") ? document.getElementById("new-char-likes-dislikes").value : "";
      const commStyle = document.getElementById("new-char-comm-style") ? document.getElementById("new-char-comm-style").value : "";
      const charSummary = document.getElementById("new-char-summary-direct") ? document.getElementById("new-char-summary-direct").value : "";

      try {
        const res = await fetch("/api/characters/create", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({
            name: name,
            first_mes: firstMes,
            personality: personality,
            persona: persona,
            gender: gender,
            age: age,
            status: status,
            role_goals: roleGoals,
            sex_preference: sexPreference,
            likes_dislikes: likesDislikes,
            communication_style: commStyle,
            char_summary: charSummary,
            avatar_base64: newCharAvatarBase64,
            outfit_overrides: (() => {
              const ov = {};
              const sMap = {
                "outer": "create-slot-outer",
                "top": "create-slot-top",
                "bottom": "create-slot-bottom",
                "socks": "create-slot-socks",
                "shoes": "create-slot-shoes",
                "neck_acc": "create-slot-neck_acc"
              };
              for (const [slot, id] of Object.entries(sMap)) {
                const el = document.getElementById(id);
                if (el && el.value) ov[slot] = el.value;
              }
              return Object.keys(ov).length > 0 ? ov : null;
            })()
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "สร้างตัวละครไม่สำเร็จ");
        closeCharCreateModal();
        alert(`✓ สร้างตัวละคร ${name} เรียบร้อยแล้ว!`);
        await loadCharacters();
        selectCharacter(name);
      } catch (e) {
        alert("❌ ข้อError: " + e.message);
      }
    }

    // --- CHARACTER CARD EDIT MODAL ---
    async function openCharEditModal(charName) {
      editingCharName = charName;
      const modal = document.getElementById("char-edit-modal");
      document.getElementById("char-edit-name").innerText = charName;
      document.getElementById("char-edit-avatar").src = `/api/characters/${encodeURIComponent(charName)}/avatar`;

      try {
        const res = await fetch(`/api/characters/${encodeURIComponent(charName)}/state`, {
          headers: { "Authorization": `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          const base = data.baseline || {};
          document.getElementById("char-edit-firstmes").value = base.first_mes || "";
          document.getElementById("char-edit-personality").value = base.personality || "";
          document.getElementById("char-edit-persona").value = base.persona || "";
          document.getElementById("char-edit-scenario").value = base.scenario || "";
        }
      } catch (e) {}
      modal.style.display = "flex";
    }
    function openCharEditModalCurrent() {
      if (activeCharacter) openCharEditModal(activeCharacter);
    }
    function closeCharEditModal() {
      document.getElementById("char-edit-modal").style.display = "none";
      editingCharName = null;
    }
    function closeCharEditModalOnBackdrop(e) {
      if (e.target.id === "char-edit-modal") closeCharEditModal();
    }
    async function saveCharEditModal() {
      if (!editingCharName) return;
      const firstMes = document.getElementById("char-edit-firstmes").value;
      const personality = document.getElementById("char-edit-personality").value;
      const persona = document.getElementById("char-edit-persona").value;
      const scenario = document.getElementById("char-edit-scenario").value;

      try {
        const res = await fetch(`/api/characters/${encodeURIComponent(editingCharName)}/card`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({
            character_name: editingCharName,
            first_mes: firstMes,
            personality: personality,
            persona: persona,
            scenario: scenario
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "บันทึกการ์ดไม่สำเร็จ");
        const savedName = editingCharName;
        closeCharEditModal();
        showNotice(`บันทึกการ์ดตัวละคร ${savedName} แล้ว`);
        await loadCharacters();
        if (activeCharacter === savedName) selectCharacter(savedName);
      } catch (e) {
        alert("❌ ข้อError: " + e.message);
      }
    }
    function exportCharCardFromModal() {
      if (editingCharName) {
        window.location.href = `/api/characters/${encodeURIComponent(editingCharName)}/export`;
      }
    }

    // --- ENGINE & SETTINGS LOGIC ---
    async function loadEngineModelsDropdown(selModel = "") {
      const select = document.getElementById("rail-engine-model");
      const alertBox = document.getElementById("engine-setup-alert");
      const alertText = document.getElementById("engine-setup-alert-text");
      if (!select) return;
      try {
        const res = await fetch("/api/engine/models", {
          headers: { "Authorization": `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          const models = data.models || [];
          const hasExe = data.has_server_exe;

          select.innerHTML = "";
          if (models.length === 0) {
            select.innerHTML = '<option value="">-- No .gguf models found in models/ --</option>';
          } else {
            models.forEach(m => {
              const opt = document.createElement("option");
              opt.value = m.filename;
              opt.textContent = `${m.filename} (${m.size})`;
              if (m.filename === selModel) opt.selected = true;
              select.appendChild(opt);
            });
          }

          if (alertBox && alertText) {
            let warnings = [];
            if (!hasExe) {
              warnings.push("ยังไม่พบ <code>llama-server.exe</code> (นำไปวางใน <code>runtime/llama/</code> หรือโฟลเดอร์โปรเจกต์)");
            }
            if (models.length === 0) {
              warnings.push("ยังไม่พบไฟล์โมเดล <code>.gguf</code> (ดาวน์โหลดแล้ววางใน <code>models/text/</code>)");
            }
            if (warnings.length > 0) {
              alertText.innerHTML = warnings.join("<br>");
              alertBox.style.display = "block";
            } else {
              alertBox.style.display = "none";
            }
          }
        }
      } catch (e) {}
    }

    async function loadVisionModelsDropdown(selVision = "") {
      const select = document.getElementById("rail-engine-vision");
      if (!select) return;
      try {
        const res = await fetch("/api/engine/vision_models", {
          headers: { "Authorization": `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          select.innerHTML = '<option value="">None (Disable Vision)</option>';
          (data.models || []).forEach(m => {
            const opt = document.createElement("option");
            opt.value = m.filename;
            opt.textContent = `👁️ ${m.filename}`;
            if (m.filename === selVision) opt.selected = true;
            select.appendChild(opt);
          });
        }
      } catch (e) {}
    }

    let availableVoiceModels = [];
    let availableIndexFiles = [];
    let availableVoiceParams = {};
    let availableTtsVoices = [];

    async function loadTTSVoicesDropdown(selVoice = "") {
      const select = document.getElementById("rail-voice-tts");
      if (!select) return;
      try {
        const res = await fetch("/api/voice/voices", {
          headers: { "Authorization": `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          availableTtsVoices = data.voices || [];
          if (availableTtsVoices.length > 0) {
            // Group by language
            const groups = {};
            availableTtsVoices.forEach(v => {
              const lang = v.language || v.locale || "Other";
              if (!groups[lang]) groups[lang] = [];
              groups[lang].push(v);
            });
            let html = "";
            for (const [lang, vList] of Object.entries(groups)) {
              html += `<optgroup label="🌐 ${lang}">`;
              vList.forEach(v => {
                const isSel = (v.id === selVoice || (!selVoice && v.id === "th-TH-PremwadeeNeural"));
                html += `<option value="${v.id}" ${isSel ? 'selected' : ''}>${v.name}</option>`;
              });
              html += `</optgroup>`;
            }
            select.innerHTML = html;
            if (selVoice) select.value = selVoice;
          }
        }
      } catch (e) {
        console.error("loadTTSVoicesDropdown error:", e);
      }
    }

    async function loadRVCModelsDropdown(selRvc = "", selIndex = "") {
      const select = document.getElementById("rail-voice-rvc-model");
      const modalSelect = document.getElementById("setting-rvc-model");
      try {
        const res = await fetch("/api/models/list", {
          headers: { "Authorization": `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          availableVoiceModels = data.voice_models || [];
          availableIndexFiles = data.index_files || [];
          availableVoiceParams = data.voice_params || {};

          const opts = '<option value="">-- Select RVC Model --</option>' + availableVoiceModels.map(m => 
            `<option value="${m.path}" ${m.path === selRvc ? 'selected' : ''}>🎙️ ${m.name}</option>`
          ).join('');
          if (select) select.innerHTML = opts;
          if (modalSelect) modalSelect.innerHTML = opts;

          populateIndexDropdown(selIndex);
          updateParamsJsonDisplay();
        }
      } catch (e) {
        console.error("loadRVCModelsDropdown error:", e);
      }
    }

    function populateIndexDropdown(selIndex = "") {
      const indexSelect = document.getElementById("rail-voice-rvc-index");
      if (!indexSelect) return;
      let opts = '<option value="">(Auto) Automatically detect .index file</option><option value="none">🚫 Do not use Feature Index</option>';
      opts += availableIndexFiles.map(idx => 
        `<option value="${idx.path}" ${idx.path === selIndex ? 'selected' : ''}>📁 ${idx.name}</option>`
      ).join('');
      indexSelect.innerHTML = opts;
      if (selIndex) indexSelect.value = selIndex;
    }

    function onRvcModelChanged() {
      const modelPath = document.getElementById("rail-voice-rvc-model")?.value || "";
      if (modelPath) {
        const filename = modelPath.split(/[\/\\]/).pop();
        const stem = filename.substring(0, filename.lastIndexOf('.')) || filename;
        
        const paramKeys = [`${stem}_params.json`, `${stem}.json`, "params.json"];
        let matchedParams = null;
        for (const pk of paramKeys) {
          if (availableVoiceParams[pk]) {
            matchedParams = availableVoiceParams[pk];
            break;
          }
        }

        if (matchedParams) {
          if (matchedParams.defaultTune !== undefined) {
            const pitchInput = document.getElementById("rail-voice-pitch");
            if (pitchInput) pitchInput.value = matchedParams.defaultTune;
          }
          if (matchedParams.defaultIndexRatio !== undefined) {
            const irInput = document.getElementById("rail-voice-index-rate");
            const irVal = document.getElementById("rail-voice-index-rate-val");
            if (irInput) {
              irInput.value = matchedParams.defaultIndexRatio;
              if (irVal) irVal.innerText = matchedParams.defaultIndexRatio;
            }
          }
          if (matchedParams.defaultProtect !== undefined) {
            const prInput = document.getElementById("rail-voice-protect");
            const prVal = document.getElementById("rail-voice-protect-val");
            if (prInput) {
              prInput.value = matchedParams.defaultProtect;
              if (prVal) prVal.innerText = matchedParams.defaultProtect;
            }
          }
          if (matchedParams.indexFile) {
            const matchedIdx = availableIndexFiles.find(idx => idx.name === matchedParams.indexFile || idx.name.includes(matchedParams.indexFile));
            if (matchedIdx) {
              const indexSelect = document.getElementById("rail-voice-rvc-index");
              if (indexSelect) indexSelect.value = matchedIdx.path;
            }
          }
        } else {
          const matchingIdx = availableIndexFiles.find(idx => idx.name.toLowerCase().startsWith(stem.toLowerCase()));
          if (matchingIdx) {
            const indexSelect = document.getElementById("rail-voice-rvc-index");
            if (indexSelect) indexSelect.value = matchingIdx.path;
          }
        }
      }
      updateParamsJsonDisplay();
      autoSaveVoiceSettings();
    }

    function updateParamsJsonDisplay() {
      const modelPath = document.getElementById("rail-voice-rvc-model")?.value || "";
      const infoBox = document.getElementById("rail-voice-params-info");
      const infoText = document.getElementById("rail-voice-params-text");
      if (!infoBox || !infoText) return;

      if (!modelPath) {
        infoBox.style.display = "none";
        return;
      }
      const filename = modelPath.split(/[\/\\]/).pop();
      const stem = filename.substring(0, filename.lastIndexOf('.')) || filename;
      const paramKeys = [`${stem}_params.json`, `${stem}.json`, "params.json"];
      let matchedKey = null;
      let params = null;
      for (const pk of paramKeys) {
        if (availableVoiceParams[pk]) {
          matchedKey = pk;
          params = availableVoiceParams[pk];
          break;
        }
      }

      infoBox.style.display = "block";
      if (params) {
        infoText.innerHTML = `📄 ไฟล์คอนฟิก: <b>${matchedKey}</b> (Tune: ${params.defaultTune ?? 0}, IndexRatio: ${params.defaultIndexRatio ?? '0.75'}, Protect: ${params.defaultProtect ?? '0.33'})`;
      } else {
        infoText.innerHTML = `📝 ยังไม่มีไฟล์พารามิเตอร์สำหรับโมเดลนี้ (สามารถกดบันทึกสร้าง <b>${stem}_params.json</b> ได้)`;
      }
    }

    async function saveCurrentVoiceParams() {
      const modelPath = document.getElementById("rail-voice-rvc-model")?.value || "";
      if (!modelPath) {
        alert("กรุณาเลือกโมเดล RVC ก่อนบันทึกพารามิเตอร์");
        return;
      }
      const filename = modelPath.split(/[\/\\]/).pop();
      const stem = filename.substring(0, filename.lastIndexOf('.')) || filename;
      const pitch = parseInt(document.getElementById("rail-voice-pitch")?.value || 0);
      const rvcIndex = document.getElementById("rail-voice-rvc-index")?.value || "";
      const indexRate = parseFloat(document.getElementById("rail-voice-index-rate")?.value || 0.75);
      const protect = parseFloat(document.getElementById("rail-voice-protect")?.value || 0.33);

      const confirmMsg = `ต้องการบันทึก/เขียนทับไฟล์พารามิเตอร์ ${stem}_params.json หรือไม่?\n\n- Pitch Shift (Tune): ${pitch}\n- Index File: ${rvcIndex ? rvcIndex.split(/[\\/]/).pop() : '(none)'}\n- Index Ratio: ${indexRate}\n- Protect: ${protect}`;
      if (!confirm(confirmMsg)) return;

      try {
        const res = await fetch("/api/voice/params/save", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({
            model_path: modelPath,
            pitch: pitch,
            index_file: rvcIndex,
            index_rate: indexRate,
            protect: protect
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "บันทึกพารามิเตอร์ไม่สำเร็จ");

        // Update local cache
        if (data.filename && data.params) {
          availableVoiceParams[data.filename] = data.params;
        }
        updateParamsJsonDisplay();
        showNotice(`✅ บันทึก ${data.filename} สำหรับโมเดลเรียบร้อยแล้ว`, "success");
      } catch (err) {
        alert("❌ เกิดข้อErrorในการบันทึก params.json: " + err.message);
      }
    }

    function toggleRVCUI(enabled) {
      const railBox = document.getElementById("rail-voice-rvc-options");
      if (railBox) railBox.style.display = enabled ? "flex" : "none";
      const modalBox = document.getElementById("rvc-options-box");
      if (modalBox) modalBox.style.display = enabled ? "flex" : "none";
    }

    async function startBuiltinEngine() {
      const sel = document.getElementById("rail-engine-model");
      const modelName = sel ? sel.value : "";
      if (!modelName) { alert("กรุณาเลือกโมเดล .gguf ที่ต้องการสตาร์ท"); return; }
      const visionSel = document.getElementById("rail-engine-vision");
      const mmproj = visionSel ? visionSel.value : null;

      try {
        const res = await fetch("/api/engine/start", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({ model_name: modelName, mmproj: mmproj || null })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "เริ่มโมเดลไม่สำเร็จ");
        alert(`✓ กำลังโหลดโมเดล ${modelName} เข้าสู่ VRAM...`);
        pollAllServiceStatus();
      } catch (e) {
        alert("❌ ข้อError: " + e.message);
      }
    }

    async function stopBuiltinEngine() {
      if (!confirm("Do you want to stop the Built-in LLM Engine and free VRAM?")) return;
      try {
        await fetch("/api/engine/stop", {
          method: "POST",
          headers: { "Authorization": `Bearer ${token}` }
        });
        pollAllServiceStatus();
      } catch (e) {}
    }

    let currentTunnelUrl = null;

    async function copyTunnelUrl(e) {
      if (e) e.stopPropagation();
      if (!currentTunnelUrl) {
        if (typeof showNotice === "function") {
          showNotice("ยังไม่มี Public URL ของ Tunnel ในขณะนี้", "error");
        } else {
          alert("ยังไม่มี Public URL ของ Tunnel ในขณะนี้");
        }
        return;
      }
      let copied = false;
      if (navigator.clipboard && window.isSecureContext) {
        try {
          await navigator.clipboard.writeText(currentTunnelUrl);
          copied = true;
        } catch (err) {}
      }
      if (!copied) {
        try {
          const ta = document.createElement("textarea");
          ta.value = currentTunnelUrl;
          ta.style.position = "fixed";
          ta.style.left = "-9999px";
          ta.style.top = "0";
          ta.setAttribute("readonly", "");
          document.body.appendChild(ta);
          ta.focus();
          ta.select();
          copied = document.execCommand("copy");
          document.body.removeChild(ta);
        } catch (err) {}
      }
      if (copied) {
        if (typeof showNotice === "function") {
          showNotice("✓ คัดลอก Cloudflare Tunnel URL เรียบร้อยแล้ว: " + currentTunnelUrl);
        } else {
          alert("✓ คัดลอก Cloudflare Tunnel URL เรียบร้อยแล้ว:\n" + currentTunnelUrl);
        }
      } else {
        prompt("คัดลอกลิงก์นี้:", currentTunnelUrl);
      }
    }

    async function startTunnelServer() {
      const btn = document.getElementById("btn-modal-start-tunnel");
      if (btn) { btn.disabled = true; btn.innerText = "⏳ กำลังเริ่ม..."; }
      try {
        const res = await fetch("/api/tunnel/start", {
          method: "POST",
          headers: { "Authorization": `Bearer ${token}` }
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "เริ่ม Tunnel ไม่สำเร็จ");
        pollAllServiceStatus();
        if (data.status && data.status.url) {
          alert("🎉 Cloudflare Tunnel ทำงานแล้ว!\nURL: " + data.status.url);
        } else {
          alert("✓ เริ่มรัน Tunnel แล้ว... กำลังเชื่อมต่อ Cloudflare network (ตรวจสอบไฟสีฟ้า)");
        }
      } catch (err) {
        alert("❌ ไม่สามารถเริ่ม Tunnel ได้: " + err.message);
      } finally {
        if (btn) { btn.disabled = false; btn.innerText = "▶ Start Tunnel"; }
        pollAllServiceStatus();
      }
    }

    async function stopTunnelServer() {
      if (!confirm("คุณต้องการปิด Cloudflare Tunnel และหยุดการเข้าถึงจากภายนอกใช่หรือไม่?")) return;
      try {
        await fetch("/api/tunnel/stop", {
          method: "POST",
          headers: { "Authorization": `Bearer ${token}` }
        });
        currentTunnelUrl = null;
        pollAllServiceStatus();
      } catch (err) {
        alert("❌ ปิด Tunnel ไม่สำเร็จ: " + err.message);
      }
    }

    // --- VOICE TTS & RVC SYNC LOGIC ---
    function formatVoiceRate(val) {
      const num = parseInt(val) || 0;
      return num >= 0 ? `+${num}%` : `${num}%`;
    }

    function parseVoiceRate(str) {
      if (!str) return 0;
      const num = parseInt(str.toString().replace("%", ""));
      return isNaN(num) ? 0 : num;
    }

    function onVoiceRateInput(val) {
      const formatted = formatVoiceRate(val);
      const railLabel = document.getElementById("rail-voice-rate-label");
      if (railLabel) railLabel.innerText = formatted;
      const railInput = document.getElementById("rail-voice-rate");
      if (railInput && railInput.value != val) railInput.value = val;
    }

    async function syncVoiceSettingsUI() {
      try {
        const res = await fetch("/api/settings", {
          headers: { "Authorization": `Bearer ${token}` }
        });
        if (res.ok) {
          const cfg = await res.json();
          const rvcOn = !!cfg.rvc_enabled;
          const rvcModel = cfg.rvc_model || "";
          const rvcIndex = cfg.rvc_index || "";
          const indexRate = cfg.rvc_index_rate !== undefined ? cfg.rvc_index_rate : 0.75;
          const protect = cfg.rvc_protect !== undefined ? cfg.rvc_protect : 0.33;
          const ttsVoice = cfg.tts_voice || "th-TH-PremwadeeNeural";
          const rateVal = parseVoiceRate(cfg.tts_rate || "+0%");
          ttsAutoloadEnabled = !!cfg.tts_autoload;
          ttsAutoplayEnabled = !!cfg.tts_autoplay;
          const pitch = cfg.rvc_pitch !== undefined ? cfg.rvc_pitch : 0;

          // Sync rail Voice controls
          const railTts = document.getElementById("rail-voice-tts");
          if (railTts) railTts.value = ttsVoice;
          const railCheck = document.getElementById("rail-voice-rvc-check");
          if (railCheck) railCheck.checked = rvcOn;
          const railPitch = document.getElementById("rail-voice-pitch");
          if (railPitch) railPitch.value = pitch;

          onVoiceRateInput(rateVal);

          const railRate = document.getElementById("rail-voice-index-rate");
          const railRateVal = document.getElementById("rail-voice-index-rate-val");
          if (railRate) {
            railRate.value = indexRate;
            if (railRateVal) railRateVal.innerText = indexRate;
          }

          const railProt = document.getElementById("rail-voice-protect");
          const railProtVal = document.getElementById("rail-voice-protect-val");
          if (railProt) {
            railProt.value = protect;
            if (railProtVal) railProtVal.innerText = protect;
          }

          // Sync modal Voice controls
          const modalTts = document.getElementById("setting-tts-voice");
          if (modalTts) modalTts.value = ttsVoice;
          const modalCheck = document.getElementById("setting-rvc-enabled");
          if (modalCheck) modalCheck.checked = rvcOn;
          const modalPitch = document.getElementById("setting-rvc-pitch");
          if (modalPitch) modalPitch.value = pitch;
          const autoloadInput = document.getElementById("rail-tts-autoload");
          if (autoloadInput) autoloadInput.checked = ttsAutoloadEnabled;
          const autoplayInput = document.getElementById("rail-tts-autoplay");
          if (autoplayInput) autoplayInput.checked = ttsAutoplayEnabled;

          toggleRVCUI(rvcOn);
          await loadTTSVoicesDropdown(ttsVoice);
          await loadRVCModelsDropdown(rvcModel, rvcIndex);
        }
      } catch (e) {
        console.error("syncVoiceSettingsUI error:", e);
      }
    }

    async function onRvcCheckboxChanged(checked) {
      toggleRVCUI(checked);
      const modalCheck = document.getElementById("setting-rvc-enabled");
      if (modalCheck) modalCheck.checked = checked;
      await autoSaveVoiceSettings(false);
    }

    async function onTtsAutomationChanged() {
      let autoload = !!document.getElementById("rail-tts-autoload")?.checked;
      const autoplay = !!document.getElementById("rail-tts-autoplay")?.checked;
      if (autoplay) autoload = true;
      ttsAutoloadEnabled = autoload;
      ttsAutoplayEnabled = autoplay;
      const autoloadInput = document.getElementById("rail-tts-autoload");
      if (autoloadInput) autoloadInput.checked = autoload;
      await autoSaveVoiceSettings(false);
    }

    async function autoSaveVoiceSettings(showAlert = false) {
      const voice = document.getElementById("rail-voice-tts")?.value || "th-TH-PremwadeeNeural";
      const rateVal = parseInt(document.getElementById("rail-voice-rate")?.value || 0);
      const rateStr = formatVoiceRate(rateVal);
      const rvcOn = document.getElementById("rail-voice-rvc-check")?.checked || false;
      const rvcModel = document.getElementById("rail-voice-rvc-model")?.value || "";
      const rvcIndex = document.getElementById("rail-voice-rvc-index")?.value || "";
      const pitch = parseInt(document.getElementById("rail-voice-pitch")?.value || 0);
      const indexRate = parseFloat(document.getElementById("rail-voice-index-rate")?.value || 0.75);
      const protect = parseFloat(document.getElementById("rail-voice-protect")?.value || 0.33);
      const autoload = !!document.getElementById("rail-tts-autoload")?.checked;
      const autoplay = !!document.getElementById("rail-tts-autoplay")?.checked;

      // Sync modal elements
      const mVoice = document.getElementById("setting-tts-voice");
      if (mVoice) mVoice.value = voice;
      const mCheck = document.getElementById("setting-rvc-enabled");
      if (mCheck) mCheck.checked = rvcOn;
      const mModel = document.getElementById("setting-rvc-model");
      if (mModel) mModel.value = rvcModel;
      const mPitch = document.getElementById("setting-rvc-pitch");
      if (mPitch) mPitch.value = pitch;

      try {
        const res = await fetch("/api/settings", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({
            tts_voice: voice,
            tts_rate: rateStr,
            tts_autoload: autoload,
            tts_autoplay: autoplay,
            rvc_enabled: rvcOn,
            rvc_model: rvcModel,
            rvc_pitch: pitch,
            rvc_index: rvcIndex,
            rvc_index_rate: indexRate,
            rvc_protect: protect
          })
        });
        if (res.ok) {
          pollAllServiceStatus();
          if (showAlert) {
            showNotice("Save Voice Settingsแล้ว");
          }
        }
      } catch (e) {
        console.error("autoSaveVoiceSettings error:", e);
      }
    }

    async function testVoiceAudio() {
      const btn = document.getElementById("btn-test-voice");
      const voice = document.getElementById("rail-voice-tts").value;
      const rateVal = parseInt(document.getElementById("rail-voice-rate")?.value || 0);
      const rateStr = formatVoiceRate(rateVal);
      const rvcOn = document.getElementById("rail-voice-rvc-check").checked;
      const rvcModel = document.getElementById("rail-voice-rvc-model").value;
      const rvcIndex = document.getElementById("rail-voice-rvc-index")?.value || "";
      const pitch = parseInt(document.getElementById("rail-voice-pitch").value || 0);
      const indexRate = parseFloat(document.getElementById("rail-voice-index-rate")?.value || 0.75);
      const protect = parseFloat(document.getElementById("rail-voice-protect")?.value || 0.33);

      if (rvcOn && !rvcModel) {
        alert("กรุณาเลือกโมเดลเสียง RVC (.pth / .onnx) จากรายการก่อนกดทดสอบ");
        return;
      }

      if (btn) {
        btn.disabled = true;
        btn.innerText = rvcOn ? "⏳ กำลังแปลงเสียงผ่าน RVC..." : "⏳ กำลังสร้างเสียง...";
      }

      try {
        const res = await fetch("/api/voice/speak", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({
            text: "สวัสดีค่ะ นี่คือเสียงทดสอบระบบ RealmPlay",
            voice: voice,
            rate: rateStr,
            pitch: pitch,
            rvc_model: rvcOn ? rvcModel : null,
            rvc_index: rvcOn ? rvcIndex : null,
            rvc_index_rate: rvcOn ? indexRate : null,
            rvc_protect: rvcOn ? protect : null
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "สร้างเสียงไม่สำเร็จ");
        if (data.audio_url) {
          const audio = new Audio(data.audio_url);
          audio.play();
          if (rvcOn && !data.rvc_used) {
            alert("⚠️ ระบบเล่นเสียงสำรองแบบ Edge-TTS เนื่องจากโมเดล RVC เกิดข้อError ตรวจสอบโมเดลที่เลือก");
          }
        }
      } catch (e) {
        alert("❌ ข้อErrorในการแปลงเสียง: " + e.message);
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.innerText = "🔊 ทดสอบเสียง";
        }
      }
    }

    async function openSettingsModal() {
      document.getElementById("settings-modal").style.display = "flex";
      await Promise.all([syncVoiceSettingsUI(), pollAllServiceStatus()]);
    }
    function closeSettingsModal() {
      document.getElementById("settings-modal").style.display = "none";
    }
    function closeSettingsModalOnBackdrop(e) {
      if (e.target.id === "settings-modal") closeSettingsModal();
    }

    let realmPlayRestarting = false;
    async function restartRealmPlay() {
      if (realmPlayRestarting) return;
      if (!await openConfirmDialog("รีสตาร์ท RealmPlay เดี๋ยวนี้หรือไม่? คำขอที่กำลังทำงานอยู่จะถูกขัดจังหวะชั่วขณะ", "ยืนยันการรีสตาร์ท RealmPlay")) return;

      const button = document.getElementById("btn-restart-realmplay");
      realmPlayRestarting = true;
      if (button) { button.disabled = true; button.textContent = "↻ Restarting…"; }

      try {
        const response = await fetch("/api/system/restart", {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` }
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.detail || "Restart request failed");

        closeSettingsModal();
        showNotice("RealmPlay is restarting…");
        await new Promise(resolve => setTimeout(resolve, 2500));

        const deadline = Date.now() + 45000;
        while (Date.now() < deadline) {
          try {
            const ready = await fetch(`/api/auth/me?restart_check=${Date.now()}`, {
              cache: "no-store",
              headers: { Authorization: `Bearer ${token}` }
            });
            if (ready.ok) {
              window.location.reload();
              return;
            }
          } catch (_) {
            // The connection dropping briefly is expected during restart.
          }
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
        throw new Error("RealmPlay did not come back online within 45 seconds");
      } catch (error) {
        realmPlayRestarting = false;
        if (button) { button.disabled = false; button.textContent = "↻ Restart"; }
        showNotice(error.message || "Restart failed", "error");
      }
    }

    async function syncProactiveSettings() {
      try {
        const res = await fetch("/api/configuration", { headers: { "Authorization": `Bearer ${token}` } });
        if (!res.ok) throw new Error("โหลด Proactive timing ไม่สำเร็จ");
        const data = await res.json();
        const proactive = data.proactive || {};
        const minDelay = document.getElementById("proactive-min-seconds");
        const maxDelay = document.getElementById("proactive-max-seconds");
        const maxReplies = document.getElementById("proactive-max-consecutive");
        if (minDelay) minDelay.value = proactive.min_interval_seconds ?? 180;
        if (maxDelay) maxDelay.value = proactive.max_interval_seconds ?? 360;
        if (maxReplies) maxReplies.value = proactive.max_consecutive ?? 2;
      } catch (error) {
        console.warn("syncProactiveSettings:", error);
        showNotice("โหลด Proactive timing ไม่สำเร็จ", "error");
      }
    }

    function readProactiveSettings() {
      const minDelay = Number.parseInt(document.getElementById("proactive-min-seconds")?.value || "180", 10);
      const maxDelay = Number.parseInt(document.getElementById("proactive-max-seconds")?.value || "360", 10);
      const maxReplies = Number.parseInt(document.getElementById("proactive-max-consecutive")?.value || "2", 10);
      if (!Number.isInteger(minDelay) || minDelay < 30 || minDelay > 86400) throw new Error("Minimum proactive delay must be 30–86400 seconds");
      if (!Number.isInteger(maxDelay) || maxDelay < minDelay || maxDelay > 86400) throw new Error("Maximum proactive delay must be at least the minimum and no more than 86400 seconds");
      if (!Number.isInteger(maxReplies) || maxReplies < 1 || maxReplies > 2) throw new Error("Maximum proactive replies must be 1–2");
      return { min_interval_seconds: minDelay, max_interval_seconds: maxDelay, max_consecutive: maxReplies };
    }

    async function saveEngineProactiveSettings() {
      try {
        const res = await fetch("/api/configuration", {
          method: "POST",
          headers: {"Content-Type":"application/json", "Authorization":`Bearer ${token}`},
          body: JSON.stringify({ proactive:readProactiveSettings() })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Save Proactive timing ไม่สำเร็จ");
        showNotice("Save Proactive timing แล้ว");
        startProactivePresencePolling();
      } catch (error) {
        showNotice(error.message, "error");
      }
    }

    const slimRuleElementIds = {
      proactive_auto_reply: "rail-rule-proactive-auto-reply",
      proactive_state: "rail-rule-proactive-state",
      image_trigger: "rail-rule-image-trigger",
      auto_wardrobe: "rail-rule-auto-wardrobe",
      loop_guard: "rail-rule-loop-guard",
      prohibitions: "rail-rule-prohibitions",
      thinking_mode: "rail-rule-thinking-mode",
      expressive_vocalization: "rail-rule-vocalization",
      cnc_roleplay_enabled: "rail-rule-cnc-roleplay",
      trace_prompts: "rail-rule-trace-prompts"
    };

    function applyRuleSettingsToControls(rules, ids, nsfwId) {
      for (const [key, id] of Object.entries(ids)) {
        const input = document.getElementById(id);
        if (input) input.checked = rules[key] !== false;
      }
      const nsfw = document.getElementById(nsfwId);
      if (nsfw) nsfw.value = rules.nsfw_mode || "local";
    }

    async function syncSlimRuleSettings() {
      try {
        const res = await fetch("/api/configuration", { headers: { "Authorization": `Bearer ${token}` } });
        if (!res.ok) throw new Error("โหลด Rules ไม่สำเร็จ");
        const data = await res.json();
        applyRuleSettingsToControls(data.rules || {}, slimRuleElementIds, "rail-rule-nsfw-mode");
      } catch (error) {
        showNotice("โหลด Rule settings ไม่สำเร็จ", "error");
      }
    }

    function readSlimRuleSettings() {
      const rules = {};
      for (const [key, id] of Object.entries(slimRuleElementIds)) rules[key] = !!document.getElementById(id)?.checked;
      rules.nsfw_mode = document.getElementById("rail-rule-nsfw-mode")?.value || "local";
      return rules;
    }

    async function saveSlimRuleSettings() {
      try {
        const payload = { rules: readSlimRuleSettings() };
        if (typeof window.getMovableRulePriority === "function") {
          payload.rule_priority = window.getMovableRulePriority();
        }
        const res = await fetch("/api/configuration", {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
          body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error((await res.json()).detail || "บันทึก Rules ไม่สำเร็จ");
        await syncSlimRuleSettings();
        showNotice("บันทึก Rules แล้ว");
      } catch (error) {
        showNotice("บันทึก Rules ไม่สำเร็จ: " + error.message, "error");
      }
    }

    async function saveSettingsModal() {
      const comfy = (document.getElementById("setting-comfy-address")?.value || document.getElementById("rail-comfy-addr")?.value || "").trim();

      const temp = parseFloat(document.getElementById("rp-temperature")?.value || 0.7);
      const topp = parseFloat(document.getElementById("rp-top_p")?.value || 0.9);
      const rep = parseFloat(document.getElementById("rp-repetition_penalty")?.value || 1.1);

      try {
        const settingsRes = await fetch("/api/settings", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({
            llm_provider: "builtin",
            llm_temperature: temp,
            llm_top_p: topp,
            llm_repetition_penalty: rep,
            comfy_address: comfy || "http://127.0.0.1:8188"
          })
        });
        if (!settingsRes.ok) throw new Error((await settingsRes.json()).detail || "บันทึกการตั้งค่าระบบไม่สำเร็จ");
        closeSettingsModal();
        await syncVoiceSettingsUI();
        showNotice("บันทึกการตั้งค่าระบบแล้ว");
        pollAllServiceStatus();
      } catch (e) {
        showNotice("บันทึกไม่สำเร็จ: " + e.message, "error");
      }
    }

    let activeManualComfyAbortController = null;

    async function requestComfyImage(prompt) {
      activeManualComfyAbortController = new AbortController();
      try {
        const customW = parseInt(document.getElementById("rp-width")?.value || "", 10) || undefined;
        const customH = parseInt(document.getElementById("rp-height")?.value || "", 10) || undefined;
        const res = await fetch("/api/image/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
          signal: activeManualComfyAbortController.signal,
          body: JSON.stringify({
            prompt,
            character_name: activeCharacter || null,
            ...(customW ? { width: customW } : {}),
            ...(customH ? { height: customH } : {})
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || `สร้างภาพไม่สำเร็จ (${res.status})`);
        if (!data.image_url) throw new Error("ComfyUI ไม่ส่งรูปภาพกลับมา");
        const result = document.getElementById("imagegen-result");
        const image = document.getElementById("imagegen-result-image");
        const link = document.getElementById("imagegen-result-link");
        if (result && image && link) {
          image.src = `${data.image_url}?v=${Date.now()}`;
          link.href = data.image_url;
          result.style.display = "block";
        }
        showNotice("สร้างภาพเสร็จแล้ว");
        return data;
      } finally {
        activeManualComfyAbortController = null;
      }
    }

    async function triggerComfyGen() {
      switchSlimTab("imagegen");
      document.getElementById("rail-image-prompt")?.focus();
      showNotice("ใส่ Prompt แล้วกดสร้างภาพ");
    }

    async function triggerComfyGenManual(button) {
      if (activeManualComfyAbortController) {
        // User clicked while loading -> stop image generation!
        stopImageGeneration();
        if (button) button.textContent = "⏳ กำลังหยุด...";
        return;
      }

      const p = document.getElementById("rail-image-prompt").value.trim();
      if (!p) { showNotice("กรุณาระบุ Prompt", "error"); return; }
      const originalLabel = button?.textContent;
      if (button) {
        button.textContent = "⏹ คลิกเพื่อหยุด (Stop)";
        button.classList.add("btn-danger");
      }
      try {
        await requestComfyImage(p);
      } catch (e) {
        if (e.name === "AbortError") {
          console.log("Manual image gen aborted.");
        } else {
          showNotice("สร้างภาพไม่สำเร็จ: " + e.message, "error");
        }
      } finally {
        if (button) {
          button.disabled = false;
          button.textContent = originalLabel;
          button.classList.remove("btn-danger");
        }
      }
    }

    function escapeHtml(str) {
      if (!str) return "";
      return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
    }

    // Keep parameter help above all panels, including scrolling sidebars and modals.
    (function initGlobalParameterTooltips() {
      const tooltip = document.createElement("div");
      tooltip.className = "global-parameter-tooltip";
      tooltip.id = "global-parameter-tooltip";
      tooltip.setAttribute("role", "tooltip");
      document.body.appendChild(tooltip);

      let activeButton = null;
      function positionTooltip(button) {
        const rect = button.getBoundingClientRect();
        const margin = 12;
        const tooltipWidth = tooltip.offsetWidth || 280;
        const tooltipHeight = tooltip.offsetHeight || 0;
        const left = Math.max(margin, Math.min(rect.left + (rect.width / 2) - (tooltipWidth / 2), window.innerWidth - tooltipWidth - margin));
        const top = rect.top - tooltipHeight - 9;
        tooltip.style.left = `${left}px`;
        tooltip.style.top = `${Math.max(margin, top)}px`;
      }
      function showTooltip(button) {
        const content = button.querySelector(".parameter-tooltip");
        if (!content) return;
        activeButton = button;
        tooltip.textContent = content.textContent;
        tooltip.classList.add("is-visible");
        positionTooltip(button);
      }
      function hideTooltip(button) {
        if (button && activeButton !== button) return;
        tooltip.classList.remove("is-visible");
        activeButton = null;
      }

      // Delegate events so controls inserted later by Feature Settings receive help too.
      document.addEventListener("mouseover", (event) => {
        const button = event.target.closest(".parameter-help");
        if (button && !button.contains(event.relatedTarget)) showTooltip(button);
      });
      document.addEventListener("mouseout", (event) => {
        const button = event.target.closest(".parameter-help");
        if (button && !button.contains(event.relatedTarget)) hideTooltip(button);
      });
      document.addEventListener("focusin", (event) => {
        const button = event.target.closest(".parameter-help");
        if (button) showTooltip(button);
      });
      document.addEventListener("focusout", (event) => {
        const button = event.target.closest(".parameter-help");
        if (button) hideTooltip(button);
      });
      window.addEventListener("resize", () => activeButton && positionTooltip(activeButton));
      window.addEventListener("scroll", () => activeButton && positionTooltip(activeButton), true);
    })();
  