Page({
  data: {
    showDetail: false, // 是否显示详情
    detailStyle: '', // 动画样式
    currentNews: null, // 当前详情数据
    relatedNews: [], // 相关资讯
    newsId: null, // 当前资讯ID
    category: null, // 当前分类
    allNews: [], // 全部资讯数据
    // 分类映射（中英文）
    categoryMap: {
      tech: '科技',
      finance: '财经',
      sports: '体育',
      entertainment: '娱乐',
      policy: '政策'
    }
  },

  // ====================== 动画相关 ======================
  // 初始化动画
  initAnimation() {
    this.animation = wx.createAnimation({
      duration: 500,
      timingFunction: 'ease-out',
      delay: 0,
      transformOrigin: '50% 50% 0'
    });
  },

  // 详情页弹跳动画
  showBounceAnimation() {
    // 初始位置：屏幕底部外
    this.animation.translateY('100%').step();
    this.setData({
      detailStyle: this.animation.export(),
      showDetail: true
    });

    // 执行弹跳逻辑
    setTimeout(() => {
      // 1. 弹到目标位置
      this.animation.translateY(0).step({ duration: 300, timingFunction: 'ease-out' });
      // 2. 轻微弹回（模拟弹跳）
      this.animation.translateY(-30).step({ duration: 100, timingFunction: 'ease-in' });
      // 3. 回到最终位置
      this.animation.translateY(0).step({ duration: 100, timingFunction: 'ease-out' });
      
      this.setData({ detailStyle: this.animation.export() });
    }, 50);
  },

  // 关闭详情页动画
  closeAnimation(callback) {
    this.animation.translateY('100%').step({ duration: 300 });
    this.setData({ detailStyle: this.animation.export() });
    // 动画结束后执行回调（如返回上一页）
    setTimeout(() => {
      callback && callback();
    }, 300);
  },

  // ====================== 数据相关 ======================
  // 初始化所有资讯数据（含政策）
  initNewsData() {
    const allNews = [
      // 科技类
      {
        id: 1,
        title: "人工智能技术取得重大突破，新型模型性能提升300%",
        image: "https://picsum.photos/600/400?random=1",
        source: "科技日报",
        time: "2小时前",
        category: "tech",
        content: "近日，人工智能领域传来重大喜讯，由国内顶尖团队研发的新型AI模型在多项指标上实现突破，性能较上一代提升300%。该模型在自然语言处理、图像识别等任务中表现出色，专家表示这将加速AI技术的商业化应用。\n\n据研发团队负责人介绍，该模型采用了全新的网络架构和训练方法，在保持高精度的同时，大幅降低了计算资源消耗。这一突破意味着AI技术将能够在更多普通设备上运行，推动智能化的普及。\n\n业内人士分析，此次突破将对多个行业产生深远影响，特别是在医疗诊断、自动驾驶、智能客服等领域，有望带来效率的显著提升和成本的降低。"
      },
      // 财经类
      {
        id: 2,
        title: "央行发布最新金融政策，市场反应积极",
        image: "https://picsum.photos/600/400?random=2",
        source: "财经时报",
        time: "5小时前",
        category: "finance",
        content: "中国人民银行今日发布最新金融政策，旨在稳定市场预期，促进经济平稳发展。政策出台后，股市反应积极，主要指数均出现不同程度上涨。分析人士认为，此次政策调整将有效缓解市场压力。\n\n本次政策主要包括降低部分金融机构存款准备金率、优化信贷结构等措施。央行表示，这些措施将增加金融机构的资金流动性，引导金融机构加大对实体经济的支持力度。\n\n数据显示，政策发布后，银行间市场利率下降0.2个百分点，小微企业贷款申请通过率提升15%，市场信心得到明显提振。"
      },
      // 体育类
      {
        id: 3,
        title: "国家篮球队公布新一期集训名单，多位新秀入选",
        image: "https://picsum.photos/600/400?random=3",
        source: "体育周报",
        time: "昨天",
        category: "sports",
        content: "国家篮球队今日公布了新一期集训名单，除了多位老将外，还有几位表现出色的新秀入选。此次集训旨在为即将到来的国际赛事做准备，教练组表示将通过集训考察更多年轻球员。\n\n本次集训名单共有24名球员入选，其中包括5名首次入选国家队的年轻球员。国家队主教练表示，选拔球员不仅看重当前表现，更注重其发展潜力和对国家队体系的适应性。\n\n集训将于下月在青岛启动，为期20天，之后球队将前往欧洲进行热身赛，为后续的世界杯预选赛做准备。"
      },
      // 娱乐类
      {
        id: 4,
        title: "年度电影节获奖名单揭晓，多部国产影片斩获大奖",
        image: "https://picsum.photos/600/400?random=4",
        source: "娱乐前线",
        time: "3天前",
        category: "entertainment",
        content: "备受关注的年度电影节昨晚落下帷幕，获奖名单正式揭晓。多部国产影片表现亮眼，在多个重要奖项中有所斩获。业内人士表示，这标志着中国电影产业的持续发展和进步。\n\n其中，国产影片《山河故人》获得最佳影片奖，该片以独特的叙事手法和深刻的人文关怀赢得了评委的一致好评。导演张艺谋凭借《长城》获得最佳导演奖，这是他职业生涯中获得的第12个重要导演奖项。\n\n此外，最佳男主角由演员吴京获得，最佳女主角由周冬雨获得，两位演员在影片中的表现得到了广泛认可。"
      },
      // 政策类（报废车相关）
      {
        id: 5,
        title: "2023年报废车回收政策解读",
        image: "https://picsum.photos/600/400?random=6",
        source: "政策法规网",
        time: "1天前",
        category: "policy",
        content: "国家发展改革委、工信部近日联合发布《关于进一步规范报废机动车回收拆解管理的通知》，明确2024年1月1日起正式实施新的报废车回收政策。此次政策调整主要聚焦以下三大方面：\n\n一、回收流程规范化：要求回收企业必须通过国家备案，车主需提供身份证、行驶证等证明文件，杜绝“黑回收”“黑拆解”现象。同时，建立全国统一的报废车回收信息平台，实现“一车一档”全程可追溯。\n\n二、评估价格透明化：政策要求回收企业公开评估标准，不得低于行业指导价收购。对铝车身、铁车身等不同材质车辆，明确最低评估系数，保障车主合法权益。\n\n三、环保要求升级：拆解过程需符合《固体废物污染环境防治法》，危险废物需交由有资质企业处理，违规企业将面临最高50万元罚款。\n\n此外，政策还提出对提前报废老旧车辆的车主给予补贴，具体标准由各省市根据当地情况制定，预计补贴金额在1000-5000元不等。"
      },
      // 政策类（补充数据，用于相关推荐）
      {
        id: 6,
        title: "报废车回收行业监管细则出台，3类企业将被重点整治",
        image: "https://picsum.photos/600/400?random=7",
        source: "中国环境报",
        time: "2天前",
        category: "policy",
        content: "为配合2024年报废车回收新政实施，生态环境部近日发布《报废机动车拆解企业环境监管细则》，明确将对3类企业进行重点整治：\n\n1. 未取得拆解资质却擅自开展业务的“黑作坊”；\n2. 拆解过程中违规排放污染物的企业；\n3. 倒卖报废车零部件、伪造回收证明的企业。\n\n细则要求地方环保部门每季度开展一次抽查，对违规企业依法责令整改，情节严重的吊销资质证书。同时，鼓励公众举报违规行为，举报查实后给予200-1000元奖励。"
      }
    ];

    this.setData({ allNews }, () => {
      // 数据初始化完成后加载详情
      this.loadNewsDetail();
    });
  },

  // 加载当前资讯详情
  loadNewsDetail() {
    const { newsId, allNews, category } = this.data;
    // 查找当前资讯
    const currentNews = allNews.find(item => item.id === newsId);
    if (!currentNews) {
      wx.showToast({ title: '详情数据异常', icon: 'none' });
      this.closeDetail();
      return;
    }
    // 查找相关资讯（同分类、不同ID，取前3条）
    const relatedNews = allNews.filter(
      item => item.category === category && item.id !== newsId
    ).slice(0, 3);
    // 更新数据并执行动画
    this.setData({ currentNews, relatedNews }, () => {
      this.showBounceAnimation();
    });
  },

  // ====================== 页面跳转/关闭 ======================
  // 跳转到相关资讯
  navigateToRelated(e) {
    const newsId = e.currentTarget.dataset.id;
    // 关闭当前详情动画
    this.closeAnimation(() => {
      wx.redirectTo({
        url: `/pages/newsdetail/newsdetail?newsId=${newsId}&category=${this.data.category}`
      });
    });
  },

  // 关闭详情页（返回上一页）
  closeDetail() {
    this.closeAnimation(() => {
      wx.navigateBack({ delta: 1 }); // 返回上一页
    });
  },

  // ====================== 页面生命周期 ======================
  onLoad(options) {
    // 获取跳转参数
    const newsId = parseInt(options.newsId);
    const category = options.category || 'all';
    this.setData({ newsId, category });
    // 初始化动画和数据
    this.initAnimation();
    this.initNewsData();
  },

  // 防止页面被下拉
  onPullDownRefresh() {
    wx.stopPullDownRefresh();
  }
})