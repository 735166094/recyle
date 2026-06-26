// aboutour.js
Page({
  data: {
    // 动态数据（从接口获取）
    dynamicData: null,
    // 静态兜底数据
    staticData: {
      companyIntro: "芜湖奇瑞资源技术有限公司成立于2006年，是奇瑞控股集团全资子公司，公司成立以来，深耕城市矿产，积极探索再生资源的循环利用，推动绿色、清洁生产和合理回收、再利用、再制造的研究与产业化。公司积极围绕着汽车全产业链资源的再生利用，积极开展废钢、废铝等再生资源的循环利用，减少矿山资源的采伐。目前，公司依托奇瑞集团资源优势，在再生资源利用方面，形成了稳定的资源采购渠道和销售渠道。公司不断加大汽车零部件再制造的研发，逐步形成了再生资源回收利用、报废汽车零部件再制造再利用、动力电池综合利用等汽车产业链相关资源循环利用的核心业务，进一步提升了公司的核心能力。",
      introImg: "https://picsum.photos/id/1071/1200/600",
      stats: {
        established: "2010",
        models: "12款",
        export: "30+国家",
        patents: "1200+"
      },
      history: [{
          year: "1997",
          event: "奇瑞汽车正式成立，开启自主创新之路"
        },
        {
          year: "2010",
          event: "奇瑞新能源公司成立，专注新能源汽车研发"
        },
        {
          year: "2017",
          event: "首款纯电动SUV上市，销量突破10万辆"
        },
        {
          year: "2020",
          event: "全球研发中心落成，拥有5000+研发人员"
        },
        {
          year: "2023",
          event: "累计销量突破100万辆，出口30多个国家"
        }
      ],
      principles: [{
          id: 1,
          icon: "icon-cogs",
          title: "创新驱动",
          desc: "持续投入研发，掌握核心三电技术"
        },
        {
          id: 2,
          icon: "icon-leaf",
          title: "绿色环保",
          desc: "全产业链碳中和，打造环保出行生态"
        },
        {
          id: 3,
          icon: "icon-user",
          title: "用户至上",
          desc: "以用户需求为中心，提供优质服务"
        },
        {
          id: 4,
          icon: "icon-handshake",
          title: "开放合作",
          desc: "与全球伙伴携手，推动新能源产业发展"
        }
      ],
      contact: {
        address: "安徽省芜湖市经济技术开发区长春路8号",
        phone: "400-883-8888",
        email: "info@cheryzy.com",
        website: "https://cheryzy.com"
      }
    },
    // 状态管理
    loading: true,
    error: false,
    showBackToTop: false
  },

  onLoad() {
    // 页面加载时获取数据（5秒超时）
    this.fetchDynamicData();
  },

  // 监听页面滚动，控制返回顶部按钮
  onPageScroll(e) {
    this.setData({
      showBackToTop: e.scrollTop > 500
    });
  },

  // 获取动态数据（带5秒超时）
  fetchDynamicData() {
    // 显示加载状态
    this.setData({
      loading: true,
      error: false
    });

    // 设置超时计时器（5秒）
    const timeoutTimer = setTimeout(() => {
      this.handleRequestError("请求超时，请稍后再试");
    }, 5000);
  },

  // 处理请求错误
  handleRequestError(message) {
    // 显示错误弹窗
    wx.showToast({
      title: message,
      icon: "none",
      duration: 3000,
      mask: true
    });

    // 隐藏加载状态，保留静态数据
    this.setData({
      loading: false,
      error: true
    });
  },

  // 返回顶部
  scrollToTop() {
    wx.pageScrollTo({
      scrollTop: 0,
      duration: 300
    });
  },

  // 拨打电话
  makePhoneCall() {
    const phone = this.data.dynamicData?.contact?.phone || this.data.staticData.contact.phone;
    wx.makePhoneCall({
      phoneNumber: phone
    });
  },

  // 使用正则表达式验证URL有效性
  isValidUrl(url) {
    // 匹配http/https开头的合法URL
    const urlReg = /^(https?:\/\/)?([\da-z.-]+)\.([a-z.]{2,6})([\/\w.-]*)*\/?$/i;
    return urlReg.test(url);
  },

  // 打开官网（用户授权确认）
  openWebsite() {
    // 获取网址（优先动态数据，其次静态数据）
    const website = this.data.dynamicData?.contact?.website || this.data.staticData.contact.website;

    // 基础校验：网址是否存在
    if (!website) {
      wx.showToast({
        title: "暂无官方网站信息",
        icon: "none",
        duration: 2000
      });
      return;
    }

    // 完善URL处理：补全协议头（http/https）
    let validUrl = website.trim(); // 去除首尾空格
    if (!validUrl.startsWith('http://') && !validUrl.startsWith('https://')) {
      validUrl = `https://${validUrl}`;
    }

    // 使用正则表达式验证URL格式（替代URL构造函数）
    if (!this.isValidUrl(validUrl)) {
      wx.showToast({
        title: "网址格式不正确",
        icon: "none",
        duration: 2000
      });
      console.error("无效的URL格式:", website);
      return;
    }

    // 显示授权确认弹窗（明确告知用户跳转风险）
    wx.showModal({
      title: "访问外部网站",
      content: `即将离开小程序，跳转到：\n${validUrl}`, // 显示完整网址增强透明度
      confirmText: "继续访问",
      cancelText: "取消",
      confirmColor: "#FF4400", // 与小程序主题色一致
      success: (res) => {
        if (res.confirm) {
          // 跳转前检查webview页面是否存在（兼容处理）
          wx.navigateTo({
            url: `/pages/webview/webview?url=${encodeURIComponent(validUrl)}`,
            fail: (err) => {
              // 区分跳转失败原因
              if (err.errMsg.includes('page "pages/webview/webview" is not found')) {
                wx.showToast({
                  title: "功能未就绪，请稍后再试",
                  icon: "none",
                  duration: 2000
                });
              } else {
                wx.showToast({
                  title: "跳转失败，请重试",
                  icon: "none",
                  duration: 2000
                });
              }
              console.error("官网跳转失败：", err);
            }
          });
        } else if (res.cancel) {
          // 用户取消时不显示提示（避免干扰）
          console.log("用户取消访问外部网站");
        }
      }
    });
  }
});