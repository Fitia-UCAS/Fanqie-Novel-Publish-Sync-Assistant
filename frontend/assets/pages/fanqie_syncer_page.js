window.renderFanqieSyncerPage = function renderFanqieSyncerPage(app) {
  const cfg = app.state.config.chapter_sync || {};
  return `
    <section class="page active" data-page="chapter_sync">
      <div class="fanqie-task-grid">
        <div class="fanqie-settings-card">
          <div class="settings-body">
            <div class="form-grid">
              <div class="field">
                <label>完整小说 TXT</label>
                ${app.filePicker('syNovelFile', cfg.novelFile || '', 'syChooseNovel', '选择完整小说 TXT')}
              </div>
              <div class="field">
                <label>章节管理 URL</label>
                <input class="input" id="syUrl" value="${app.attr(cfg.chapterManageUrl || '')}" placeholder="https://fanqienovel.com/..." />
              </div>
              <div class="field-pair">
                <div class="field"><label>起始章节</label><input class="input" id="syStart" type="number" min="1" value="${app.attr(cfg.start || 1)}" /></div>
                <div class="field"><label>结束章节</label><input class="input" id="syEnd" type="number" min="1" value="${app.attr(cfg.end || 1)}" /></div>
              </div>
              <div class="group-label">同步选项</div>
              <div class="option-grid three-col">
                <label><input type="checkbox" id="syUseAi" ${cfg.useAi ? 'checked' : ''}/> 使用 AI</label>
                <label><input type="checkbox" id="syVerifyAfterPublish" ${cfg.verifyAfterPublish !== false ? 'checked' : ''}/> 列表校验</label>
                <label><input type="checkbox" id="syDebugScreenshots" ${cfg.debugScreenshots !== false ? 'checked' : ''}/> 步骤截图</label>
                <label><input type="checkbox" id="syFailureScreenshots" ${cfg.failureScreenshots !== false ? 'checked' : ''}/> 失败截图</label>
                <label><input type="checkbox" id="syGitTracking" ${cfg.gitTracking !== false ? 'checked' : ''}/> Git追踪</label>
                <label><input type="checkbox" id="syCleanBeforeRun" ${cfg.cleanBeforeRun !== false ? 'checked' : ''}/> 启动清理</label>
              </div>
              <div class="action-row two-actions sync-main-actions">
                <button class="big-action primary-action" data-sync-op="publish"><span>↻</span><div><b>开始同步</b></div></button>
                <button class="big-action primary-action" id="syStop" type="button"><span>×</span><div><b>停止同步</b></div></button>
              </div>
              <div class="action-row two-actions sync-main-actions">
                <button class="big-action" data-sync-op="pull"><span>↓</span><div><b>开始拉取</b></div></button>
                <button class="big-action" data-sync-op="compare"><span>≠</span><div><b>打开对比</b></div></button>
              </div>
            </div>
          </div>
        </div>
        ${app.renderTerminalPanel('chapter_sync')}
      </div>
    </section>
  `;
};
