// pages/mall/favorites/favorites.js
const app = getApp();
import api from '../../../config/settings';

Page({
  data: {
    favoritesList: [],
    recommendItems: [],
    selectAll: false,
    selectedCount: 0,
    loading: false,
    hasMore: true,
    page: 1,
    pageSize: 10
  },

  onLoad: function () {
    this.loadFavorites();
  },

  onShow: function () {
    // 页面显示时刷新收藏列表
    this.setData({
      page: 1,
      hasMore: true
    });
    this.loadFavorites();
  },

  /**
   * 从后端API加载收藏列表
   */
  loadFavorites: function () {
    // 检查用户是否登录
    if (!app.globalData.isLoggedIn) {
      wx.showToast({
        title: '请先登录',
        icon: 'none',
        duration: 1500
      });

      setTimeout(() => {
        wx.navigateTo({
          url: '/pages/user/login/login?redirect=/pages/mall/favorites/favorites'
        });
      }, 500);

      // 设置空状态
      this.setData({
        favoritesList: [],
        loading: false
      });
      return;
    }

    this.setData({
      loading: true
    });

    const that = this;

    wx.request({
      url: api.userFavorites,
      method: 'GET',
      header: {
        'Authorization': 'Bearer ' + app.globalData.token
      },
      data: {
        type: 'product'
      },
      success: function (res) {
        console.log('收藏列表响应:', res);
        console.log('响应数据:', res.data);
        that.setData({
          loading: false
        });

        // 检查响应数据的结构
        if (!res.data) {
          console.error('响应数据为空');
          wx.showToast({
            title: '服务器返回数据为空',
            icon: 'none',
            duration: 1500
          });
          that.setData({
            favoritesList: []
          });
          return;
        }

        let favorites = [];

        if (res.data.results && res.data.results.code === 200 && Array.isArray(res.data.results.data)) {
          favorites = res.data.results.data;
        } else if (res.data.code === 200 && Array.isArray(res.data.data)) {
          favorites = res.data.data;
        } else if (Array.isArray(res.data)) {
          // 格式: 直接返回数组
          favorites = res.data;
        } else {
          // 其他格式，尝试提取
          if (res.data.data && Array.isArray(res.data.data)) {
            favorites = res.data.data;
          }
        }

        console.log('解析到的收藏数据（处理前）:', favorites);
        console.log('favorites类型:', typeof favorites);
        console.log('favorites长度:', Array.isArray(favorites) ? favorites.length : '不是数组');

        // 确保favorites是数组
        if (!Array.isArray(favorites)) {
          console.error('favorites不是数组，无法进行map操作:', favorites);
          wx.showToast({
            title: '数据格式错误',
            icon: 'none',
            duration: 1500
          });
          that.setData({
            favoritesList: []
          });
          return;
        }

        // 格式化收藏数据
        const formattedList = favorites.map(function (item, index) {
          // 检查item结构
          console.log('单个收藏item [' + index + ']:', item);

          // 安全地获取字段
          const itemId = item.item_id !== undefined ? item.item_id :
            (item.id !== undefined ? item.id : 0);
          const favoriteId = item.id !== undefined ? item.id :
            (item.favorite_id !== undefined ? item.favorite_id : itemId);
          const title = item.item_name || item.name || item.title || '未命名商品';
          const image = item.item_image || item.image || item.main_image || '/static/tabbar/mall.png';

          // 积分价格需要从商品详情获取，这里先设为0
          // 如果需要显示积分价格，需要额外请求商品详情API
          const points = item.points || item.base_points_price || item.final_price || 0;

          console.log('解析结果: id=' + itemId + ', title=' + title + ', points=' + points);

          return {
            id: itemId, // 商品ID
            favoriteId: favoriteId, // 收藏记录ID
            title: title,
            image: image,
            points: points,
            selected: false,
            type: 'product'
          };
        });

        console.log('格式化后的收藏列表:', formattedList);

        that.setData({
          favoritesList: formattedList,
          hasMore: false
        });

        that.calculateSelected();

        // 如果没有收藏，显示推荐商品
        if (formattedList.length === 0) {
          console.log('收藏列表为空，加载推荐商品');
          that.loadRecommendItems();
        } else {
          console.log('收藏列表有数据，数量:', formattedList.length);
          // 如果有收藏，清空推荐商品
          that.setData({
            recommendItems: []
          });

          // 如果需要获取商品的价格，可以在这里额外请求
          that.loadProductsPoints(formattedList);
        }
      },
      fail: function (err) {
        console.error('加载收藏失败，错误详情:', err);
        that.setData({
          loading: false
        });
        wx.showToast({
          title: '网络错误，请检查网络连接',
          icon: 'none',
          duration: 1500
        });

        // 设置空列表
        that.setData({
          favoritesList: []
        });
      }
    });
  },

  /**
   * 批量加载商品价格信息
   */
  loadProductsPoints: function (favoritesList) {
    const that = this;
    const productIds = favoritesList.map(item => item.id).filter(id => id > 0);

    if (productIds.length === 0) {
      return;
    }

    console.log('需要获取价格的商品ID列表:', productIds);

    // 存储所有商品价格的Promise
    const pricePromises = productIds.map(productId => {
      return new Promise((resolve) => {
        wx.request({
          url: api.productDetail + productId + '/',
          method: 'GET',
          header: {
            'Authorization': 'Bearer ' + app.globalData.token
          },
          success: function (res) {
            if (res.data && res.data.id) {
              const product = res.data;
              // 尝试多种可能的积分字段
              const points = product.base_points_price ||
                product.points_price ||
                product.final_price ||
                product.price ||
                0;
              resolve({
                productId,
                points
              });
            } else {
              resolve({
                productId,
                points: 0
              });
            }
          },
          fail: function (err) {
            console.error('获取商品详情失败:', err);
            resolve({
              productId,
              points: 0
            });
          }
        });
      });
    });

    // 等待所有价格获取完成
    Promise.all(pricePromises).then(results => {
      // 创建商品ID到价格的映射
      const priceMap = {};
      results.forEach(result => {
        priceMap[result.productId] = result.points;
      });

      // 更新收藏列表的价格
      const updatedList = that.data.favoritesList.map(item => {
        if (priceMap[item.id] !== undefined) {
          return {
            ...item,
            points: priceMap[item.id]
          };
        }
        return item;
      });

      console.log('更新后的收藏列表:', updatedList);

      that.setData({
        favoritesList: updatedList
      });
    }).catch(error => {
      console.error('批量获取价格失败:', error);
    });
  },

  /**
   * 加载推荐商品
   */
  loadRecommendItems: function () {
    const that = this;
    wx.request({
      url: api.recommendednewgoods,
      method: 'GET',
      success: function (res) {
        if (res.data && res.data.length > 0) {
          const recommendItems = res.data.slice(0, 4).map(function (item) {
            return {
              id: item.id,
              title: item.name,
              image: item.main_image,
              points: item.base_points_price || 0
            };
          });
          that.setData({
            recommendItems: recommendItems
          });
        }
      },
      fail: function (err) {
        console.error('加载推荐商品失败:', err);
      }
    });
  },

  calculateSelected: function () {
    const selectedCount = this.data.favoritesList.filter(item => item.selected).length;
    const selectAll = selectedCount === this.data.favoritesList.length && this.data.favoritesList.length > 0;
    this.setData({
      selectedCount,
      selectAll
    });
  },

  onItemSelect: function (e) {
    const favoriteId = e.currentTarget.dataset.favoriteid;
    const favoritesList = this.data.favoritesList.map(item =>
      item.favoriteId === favoriteId ? {
        ...item,
        selected: !item.selected
      } : item
    );
    this.setData({
      favoritesList
    });
    this.calculateSelected();
  },

  onSelectAll: function () {
    const selectAll = !this.data.selectAll;
    const favoritesList = this.data.favoritesList.map(item => ({
      ...item,
      selected: selectAll
    }));
    this.setData({
      favoritesList,
      selectAll
    });
    this.calculateSelected();
  },

  /**
   * 批量加入购物车
   */
  addToCart: function () {
    const selected = this.data.favoritesList.filter(i => i.selected);
    if (!selected.length) return wx.showToast({
      title: '请选择商品',
      icon: 'none'
    });

    const cartData = wx.getStorageSync('cartData') || [];
    let addedCount = 0;

    selected.forEach(item => {
      const idx = cartData.findIndex(c => c.id === item.id);
      if (idx > -1) {
        cartData[idx].quantity = (cartData[idx].quantity || 1) + 1;
      } else {
        cartData.push({
          id: item.id,
          title: item.title,
          image: item.image,
          points: item.points,
          quantity: 1
        });
      }
      addedCount++;
    });

    wx.setStorageSync('cartData', cartData);
    wx.showToast({
      title: `已添加${addedCount}件商品到购物车`,
      icon: 'success'
    });
  },

  /**
   * 单个加入购物车
   */
  addToCartSingle: function (e) {
    const favoriteId = e.currentTarget.dataset.favoriteid;
    const item = this.data.favoritesList.find(i => i.favoriteId === favoriteId);
    if (!item) return;

    const cartData = wx.getStorageSync('cartData') || [];
    const idx = cartData.findIndex(c => c.id === item.id);

    if (idx > -1) {
      cartData[idx].quantity = (cartData[idx].quantity || 1) + 1;
    } else {
      cartData.push({
        id: item.id,
        title: item.title,
        image: item.image,
        points: item.points,
        quantity: 1
      });
    }

    wx.setStorageSync('cartData', cartData);
    wx.showToast({
      title: '已加入购物车',
      icon: 'success'
    });
  },

  /**
   * 批量取消收藏
   */
  deleteSelected: function () {
    const selected = this.data.favoritesList.filter(i => i.selected);
    if (!selected.length) return wx.showToast({
      title: '请选择商品',
      icon: 'none'
    });

    const that = this;
    let deleteCount = 0;
    const totalCount = selected.length;

    selected.forEach(item => {
      wx.request({
        url: api.userFavoriteDetail + item.favoriteId + '/',
        method: 'DELETE',
        header: {
          'Authorization': 'Bearer ' + app.globalData.token
        },
        success: function (res) {
          deleteCount++;
          if (deleteCount === totalCount) {
            wx.showToast({
              title: `已取消${totalCount}个收藏`,
              icon: 'success'
            });
            // 重新加载收藏列表
            that.setData({
              page: 1,
              hasMore: true
            });
            that.loadFavorites();
          }
        },
        fail: function (err) {
          console.error('取消收藏失败:', err);
          deleteCount++;
          if (deleteCount === totalCount) {
            wx.showToast({
              title: '部分操作失败，请重试',
              icon: 'none'
            });
          }
        }
      });
    });
  },

  /**
   * 单个取消收藏
   */
  deleteSingle: function (e) {
    const favoriteId = e.currentTarget.dataset.favoriteid;
    const item = this.data.favoritesList.find(i => i.favoriteId === favoriteId);
    if (!item) return;

    const that = this;
    wx.request({
      url: api.userFavoriteDetail + favoriteId + '/',
      method: 'DELETE',
      header: {
        'Authorization': 'Bearer ' + app.globalData.token
      },
      success: function (res) {
        if (res.data.code === 200) {
          wx.showToast({
            title: '取消收藏成功',
            icon: 'success'
          });
          // 从列表中移除
          const favoritesList = that.data.favoritesList.filter(i => i.favoriteId !== favoriteId);
          that.setData({
            favoritesList
          });
          that.calculateSelected();
        } else {
          wx.showToast({
            title: '取消收藏失败',
            icon: 'none'
          });
        }
      },
      fail: function (err) {
        console.error('取消收藏失败:', err);
        wx.showToast({
          title: '网络错误',
          icon: 'none'
        });
      }
    });
  },

  onItemTap: function (e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({
      url: `/pages/mall/goodsdetail/goodsdetail?id=${id}`
    });
  },

  onRecommendTap: function (e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({
      url: `/pages/mall/goodsdetail/goodsdetail?id=${id}`
    });
  },

  goToMall: function () {
    wx.switchTab({
      url: '/pages/mall/index/index'
    });
  },

  onPullDownRefresh: function () {
    setTimeout(() => {
      this.setData({
        page: 1,
        hasMore: true
      });
      this.loadFavorites();
      wx.stopPullDownRefresh();
    }, 500);
  },

  /**
   * 页面上拉触底事件的处理函数
   */
  onReachBottom: function () {
    if (this.data.hasMore && !this.data.loading) {
      this.setData({
        page: this.data.page + 1
      });
      this.loadFavorites();
    }
  }
});