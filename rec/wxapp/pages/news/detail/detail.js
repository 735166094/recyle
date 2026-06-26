import api from '../../../config/settings'

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
      all: '全部',
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
      this.animation.translateY(0).step({
        duration: 300,
        timingFunction: 'ease-out'
      });
      // 2. 轻微弹回（模拟弹跳）
      this.animation.translateY(-30).step({
        duration: 100,
        timingFunction: 'ease-in'
      });
      // 3. 回到最终位置
      this.animation.translateY(0).step({
        duration: 100,
        timingFunction: 'ease-out'
      });

      this.setData({
        detailStyle: this.animation.export()
      });
    }, 50);
  },

  // 关闭详情页动画
  closeAnimation(callback) {
    this.animation.translateY('100%').step({
      duration: 300
    });
    this.setData({
      detailStyle: this.animation.export()
    });
    // 动画结束后执行回调（如返回上一页）
    setTimeout(() => {
      callback && callback();
    }, 300);
  },

  // ====================== 数据相关 ======================
  // 图片预览
  previewImage(e) {
    const imageUrl = e.currentTarget.dataset.image;
    wx.previewImage({
      current: imageUrl, // 当前显示图片
      urls: [imageUrl], // 需要预览的图片列表
      fail: (err) => {
        console.error('预览图片失败:', err);
        wx.showToast({
          title: '预览图片失败',
          icon: 'none'
        });
      }
    });
  },

  // 加载当前资讯详情
  loadNewsDetail() {
    const {
      newsId,
      category
    } = this.data;

    // 获取新闻详情
    wx.request({
      url: `${api.news}${newsId}/`,
      method: 'GET',
      success: (res) => {
        if (res.statusCode === 200 && res.data) {
          const currentNews = res.data;

          // 增加访问量
          wx.request({
            url: `${api.news}${newsId}/increase_view_count/`,
            method: 'POST',
            success: () => {
              // console.log('访问量增加成功');
            },
            fail: (err) => {
              console.error('增加访问量失败:', err);
            }
          });

          // 获取相关新闻（同分类、不同ID，取前3条）
          wx.request({
            url: api.news,
            method: 'GET',
            data: {
              category: currentNews.category.id,
              page_size: 4 // 获取4条，可能包含当前新闻
            },
            success: (res2) => {
              if (res2.statusCode === 200 && res2.data) {
                const relatedNews = res2.data.results
                  .filter(item => item.id !== newsId)
                  .slice(0, 3)
                  .map(item => ({
                    id: item.id,
                    title: item.title,
                    image: item.image || item.image_url,
                    source: item.source,
                    time: item.publish_date
                  }));

                // 更新数据并执行动画
                this.setData({
                  currentNews,
                  relatedNews
                }, () => {
                  this.showBounceAnimation();
                });
              }
            },
            fail: (err) => {
              console.error('获取相关新闻失败:', err);
              // 即使获取相关新闻失败，也显示详情
              this.setData({
                currentNews
              }, () => {
                this.showBounceAnimation();
              });
            }
          });
        } else {
          wx.showToast({
            title: '详情数据异常',
            icon: 'none'
          });
          this.closeDetail();
        }
      },
      fail: (err) => {
        console.error('获取新闻详情失败:', err);
        wx.showToast({
          title: '获取详情失败',
          icon: 'none'
        });
        this.closeDetail();
      }
    });
  },

  // ====================== 页面跳转/关闭 ======================
  // 关闭详情页
  closeDetail() {
    this.closeAnimation(() => {
      wx.navigateBack();
    });
  },

  // 跳转到相关资讯
  navigateToRelated(e) {
    const newsId = e.currentTarget.dataset.id;
    // 关闭当前详情动画
    this.closeAnimation(() => {
      wx.redirectTo({
        url: `/pages/news/detail/detail?newsId=${newsId}&category=${this.data.category}`
      });
    });
  },

  // ====================== 页面生命周期 ======================
  onLoad(options) {
    // 获取跳转参数
    const newsId = parseInt(options.newsId);
    const category = options.category || 'all';
    this.setData({
      newsId,
      category
    });
    // 初始化动画和数据
    this.initAnimation();
    this.loadNewsDetail();
  },

  // 防止页面被下拉
  onPullDownRefresh() {
    wx.stopPullDownRefresh();
  }
})