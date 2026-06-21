window.renderFanqiePublisherPage = function renderFanqiePublisherPage(app) {
  const cfg = app.state.config.auto_publish || {};
  return `
    <section class="page active" data-page="auto_publish">
      <div class="fanqie-task-grid">
        <div class="fanqie-settings-card">
          <div class="settings-body">
            <div class="form-grid">
              <div class="field">
                <label>完整小说 TXT</label>
                ${app.filePicker('apNovelFile', cfg.novelFile || '', 'apChooseNovel', '选择完整小说 TXT')}
              </div>
              <div class="field">
                <label>章节管理 URL</label>
                <input class="input" id="apUrl" value="${app.attr(cfg.chapterManageUrl || '')}" placeholder="https://fanqienovel.com/..." />
              </div>
              <div class="field-pair">
                <div class="field"><label>起始章节</label><input class="input" id="apStart" type="number" min="1" value="${app.attr(cfg.start || 1)}" /></div>
                <div class="field"><label>结束章节</label><input class="input" id="apEnd" type="number" min="1" value="${app.attr(cfg.end || 1)}" /></div>
              </div>
              <div class="group-label">发布选项</div>
              <div class="option-grid three-col">
                <label><input type="checkbox" id="apUseAi" ${cfg.useAi ? 'checked' : ''}/> 使用 AI</label>
                <label><input type="checkbox" id="apVerifyAfterPublish" ${cfg.verifyAfterPublish !== false ? 'checked' : ''}/> 列表校验</label>
                <label><input type="checkbox" id="apDebugScreenshots" ${cfg.debugScreenshots !== false ? 'checked' : ''}/> 步骤截图</label>
                <label><input type="checkbox" id="apFailureScreenshots" ${cfg.failureScreenshots !== false ? 'checked' : ''}/> 失败截图</label>
                <label><input type="checkbox" id="apGitTracking" ${cfg.gitTracking !== false ? 'checked' : ''}/> Git追踪</label>
                <label><input type="checkbox" id="apCleanBeforeRun" ${cfg.cleanBeforeRun !== false ? 'checked' : ''}/> 启动清理</label>
              </div>
              <div class="action-row two-actions">
                <button class="big-action primary-action" data-auto-op="publish"><span>↑</span><div><b>启动发布</b></div></button>
                <button class="big-action primary-action" id="apStop" type="button"><span>×</span><div><b>停止发布</b></div></button>
              </div>
            </div>
          </div>
        </div>
        ${app.renderTerminalPanel('auto_publish')}
      </div>
    </section>
  `;
};
