App({
  globalData: {
    // 由云函数返回的会话上下文，用于多轮追问
    session: {
      scene: null,
      collected: {},
      missing: [],
      turns: 0
    },
    // 就绪播报只发一次（页面偶发重载时不重复打扰）
    readyAnnounced: false
  },

  onLaunch() {
    if (!wx.cloud) {
      console.error('[app] 当前基础库版本过低，请使用 2.2.3 及以上版本');
      return;
    }
    wx.cloud.init({
      // 云开发环境 ID（控制台 → 云开发 → 环境列表）
      env: 'cloud1-d6giks350d4b62d0b',
      traceUser: false
    });
    this.ensurePrivacy();
  },

  /**
   * 2023 年起，调用相机/相册/录音前需满足《用户隐私保护指引》授权流程。
   * 未在公众平台配置隐私指引时，此处的 requirePrivacyAuthorize 会失败，
   * 相机功能将不可用——这是必须在后台完成的配置项，不是代码问题。
   */
  ensurePrivacy() {
    if (!wx.getPrivacySetting) return;
    wx.getPrivacySetting({
      success: (res) => {
        if (res.needAuthorization) {
          wx.requirePrivacyAuthorize({
            success: () => console.log('[app] 隐私授权通过'),
            fail: (err) => console.warn('[app] 隐私授权被拒绝或未配置指引', err)
          });
        }
      }
    });
  }
});
