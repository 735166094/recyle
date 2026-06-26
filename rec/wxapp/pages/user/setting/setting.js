// setting.js
Page({
  data: {
    // 通知设置
    notifyEnabled: true,
    marketingEnabled: false,
    soundEnabled: true,

    // 通用设置
    darkMode: false,
    currentLanguage: "简体中文",
    cacheSize: "0.0",
    appVersion: "1.0.0",

    // 状态管理
    loading: false,
    loadingText: "处理中..."
  },

  onLoad() {
    // 页面加载时读取本地设置
    this.loadSettings();
    // 加载缓存大小
    this.calculateCacheSize();
  },

  onShow() {
    // 页面显示时重新计算缓存大小
    this.calculateCacheSize();
  },

  // 从本地存储加载设置
  loadSettings() {
    const notifyEnabled = wx.getStorageSync('notifyEnabled') !== false;
    const marketingEnabled = wx.getStorageSync('marketingEnabled') === true;
    const soundEnabled = wx.getStorageSync('soundEnabled') !== false;
    const darkMode = wx.getStorageSync('darkMode') === true;
    const currentLanguage = wx.getStorageSync('currentLanguage') || "简体中文";
    const appVersion = wx.getStorageSync('appVersion') || "1.0.0";

    this.setData({
      notifyEnabled,
      marketingEnabled,
      soundEnabled,
      darkMode,
      currentLanguage,
      appVersion
    });
  },

  // 计算缓存大小
  calculateCacheSize() {
    wx.getStorageInfo({
      success: (res) => {
        // 转换为MB并保留一位小数
        const cacheSize = (res.currentSize / 1024).toFixed(1);
        this.setData({
          cacheSize
        });
      },
      fail: (err) => {
        console.error('获取缓存信息失败:', err);
        this.setData({
          cacheSize: "0.0"
        });
      }
    });
  },

  // 清除缓存
  clearCache() {
    wx.showModal({
      title: '清除缓存',
      content: '确定要清除所有缓存数据吗？',
      confirmText: '清除',
      confirmColor: '#ff4d4f',
      success: (res) => {
        if (res.confirm) {
          this.executeClearCache();
        }
      }
    });
  },

  // 执行清除缓存
  executeClearCache() {
    this.setData({
      loading: true,
      loadingText: "清除中..."
    });

    // 先获取需要保留的设置
    const settingsToKeep = {
      notifyEnabled: wx.getStorageSync('notifyEnabled'),
      marketingEnabled: wx.getStorageSync('marketingEnabled'),
      soundEnabled: wx.getStorageSync('soundEnabled'),
      darkMode: wx.getStorageSync('darkMode'),
      currentLanguage: wx.getStorageSync('currentLanguage'),
      appVersion: wx.getStorageSync('appVersion')
    };

    // 清除所有存储
    wx.clearStorage({
      success: () => {
        // 恢复需要保留的设置
        Object.keys(settingsToKeep).forEach(key => {
          if (settingsToKeep[key] !== undefined && settingsToKeep[key] !== '') {
            wx.setStorageSync(key, settingsToKeep[key]);
          }
        });

        // 重新计算缓存大小
        this.calculateCacheSize();

        this.setData({
          loading: false
        });

        wx.showToast({
          title: "缓存已清除",
          icon: "success",
          duration: 2000
        });
      },
      fail: (err) => {
        console.error('清除缓存失败:', err);
        this.setData({
          loading: false
        });
        wx.showToast({
          title: "清除失败，请重试",
          icon: "none",
          duration: 2000
        });
      },
      complete: () => {
        // 如果有文件缓存需要清理，可以调用wx.cleanStorage()
        // 注意：这个API需要用户授权
        if (wx.cleanStorage) {
          wx.cleanStorage();
        }
      }
    });
  },

  // 切换消息通知
  toggleNotify(e) {
    const enabled = e.detail.value;
    this.setData({
      notifyEnabled: enabled
    });
    wx.setStorageSync('notifyEnabled', enabled);
  },

  // 切换营销推送
  toggleMarketing(e) {
    const enabled = e.detail.value;
    this.setData({
      marketingEnabled: enabled
    });
    wx.setStorageSync('marketingEnabled', enabled);
  },

  // 切换声音提醒
  toggleSound(e) {
    const enabled = e.detail.value;
    this.setData({
      soundEnabled: enabled
    });
    wx.setStorageSync('soundEnabled', enabled);
  },

  // 切换深色模式
  toggleDarkMode(e) {
    const enabled = e.detail.value;
    this.setData({
      darkMode: enabled
    });
    wx.setStorageSync('darkMode', enabled);

    wx.showToast({
      title: enabled ? "已开启深色模式" : "已关闭深色模式",
      icon: "none",
      duration: 2000
    });
  },

  // 检查更新
  checkUpdate() {
    this.setData({
      loading: true,
      loadingText: "检查中..."
    });

    // 如果有更新管理器
    if (wx.getUpdateManager) {
      const updateManager = wx.getUpdateManager();

      updateManager.onCheckForUpdate((res) => {
        // 请求完新版本信息的回调
        console.log('是否有新版本:', res.hasUpdate);

        if (!res.hasUpdate) {
          this.setData({
            loading: false
          });
          wx.showToast({
            title: "当前已是最新版本",
            icon: "none",
            duration: 2000
          });
        }
      });

      updateManager.onUpdateReady(() => {
        this.setData({
          loading: false
        });
        wx.showModal({
          title: '更新提示',
          content: '新版本已经准备好，是否重启应用？',
          success: (res) => {
            if (res.confirm) {
              // 新的版本已经下载好，调用 applyUpdate 应用新版本并重启
              updateManager.applyUpdate();
            }
          }
        });
      });

      updateManager.onUpdateFailed(() => {
        this.setData({
          loading: false
        });
        wx.showToast({
          title: "更新失败",
          icon: "none",
          duration: 2000
        });
      });
    } else {
      // 兼容处理
      setTimeout(() => {
        this.setData({
          loading: false
        });
        wx.showToast({
          title: "当前已是最新版本",
          icon: "none",
          duration: 2000
        });
      }, 1500);
    }
  },

  // 确认退出登录
  confirmLogout() {
    wx.showModal({
      title: "确认退出",
      content: "确定要退出当前账号吗？",
      confirmText: "退出",
      confirmColor: "#ff4d4f",
      success: (res) => {
        if (res.confirm) {
          this.logout();
        }
      }
    });
  },

  // 执行退出登录
  logout() {
    this.setData({
      loading: true,
      loadingText: "退出中..."
    });

    // 模拟退出登录过程
    setTimeout(() => {
      // 清除登录状态
      wx.removeStorageSync('token');
      wx.removeStorageSync('userInfo');

      this.setData({
        loading: false
      });

      // 跳转到登录页
      wx.reLaunch({
        url: '/pages/login/login'
      });
    }, 1500);
  },

  // 导航到个人资料
  navigateToProfile() {
    wx.navigateTo({
      url: '/pages/profile/profile'
    });
  },

  // 导航到账号安全
  navigateToSecurity() {
    wx.navigateTo({
      url: '/pages/security/security'
    });
  },

  // 导航到关于我们
  navigateToAbout() {
    wx.navigateTo({
      url: '/pages/user/aboutour/aboutour',
      fail: () => wx.showToast({
        title: '跳转详情失败',
        icon: 'none'
      })
    });
  },

  // 切换语言
  changeLanguage() {
    const languages = ["简体中文", "繁体中文", "English"];
    const currentIndex = languages.indexOf(this.data.currentLanguage);
    const nextIndex = (currentIndex + 1) % languages.length;

    this.setData({
      currentLanguage: languages[nextIndex]
    });
    wx.setStorageSync('currentLanguage', languages[nextIndex]);

    wx.showToast({
      title: `已切换为${languages[nextIndex]}`,
      icon: "none",
      duration: 2000
    });
  },

  // 显示用户协议
  showAgreement() {
    wx.navigateTo({
      url: '/pages/user/agreement/agreement',
      fail: () => wx.showToast({
        title: '跳转详情失败',
        icon: 'none'
      })
    });
  }
});