// pages/mall/goodsdetail/goodsdetail.js
import api from '../../../config/settings';
const app = getApp();

Page({
  data: {
    // ========== 基础数据 ==========
    goodsId: null,
    goodsDetail: null,
    cartCount: 0,
    isFavorite: false,
    favoriteId: null, // 添加收藏ID字段
    loading: true,
    error: false,
    popupType: '', // 'addCart' 或 'buyNow'

    // ========== 交互数据 ==========
    scrollTop: 0,
    currentSwiperIndex: 0,
    activeTab: 'detail',
    buyPopupVisible: false,

    // ========== 规格相关数据 ==========
    specGroups: [],
    selectedSpecs: {},
    selectedSku: null,
    currentPrice: 0,

    // ========== 状态标识 ==========
    isCalculatingPrice: false,
    priceCalculationError: false,
    isCheckingFavorite: false // 添加检查收藏状态标识
  },

  onLoad: function (options) {
    wx.setNavigationBarTitle({
      title: '商品详情'
    });

    if (options && options.id) {
      const goodsId = parseInt(options.id);
      if (isNaN(goodsId)) {
        this.handleLoadError('商品ID格式错误');
        return;
      }

      console.log('商品详情页面加载，商品ID:', goodsId);

      this.setData({
        goodsId: goodsId,
        loading: true
      });

      // 按顺序加载：先加载商品详情，然后检查收藏状态
      this.loadGoodsDetail()
        .then(() => {
          // 商品详情加载完成后检查收藏状态
          return this.checkFavoriteStatus();
        })
        .then(() => {
          this.getCartCount();
        })
        .catch(err => {
          console.error('页面初始化失败:', err);
        });
    } else {
      this.handleLoadError('缺少商品ID参数');
    }
  },

  onShow: function () {
    // 页面显示时刷新购物车数量
    this.getCartCount();

    // 如果商品ID存在，刷新收藏状态（避免重复检查）
    if (this.data.goodsId && !this.data.loading) {
      // 延迟检查，确保其他状态已更新
      setTimeout(() => {
        this.checkFavoriteStatus();
      }, 300);
    }
  },

  /**
   * 处理页面加载错误
   */
  handleLoadError: function (message) {
    console.error('页面加载错误:', message);
    this.setData({
      loading: false,
      error: true
    });
    wx.showToast({
      title: message,
      icon: 'none',
      duration: 2000
    });
  },

  onScroll: function (e) {
    this.setData({
      scrollTop: e.detail.scrollTop
    });
  },

  /**
   * 轮播图索引变化
   */
  onSwiperChange: function (e) {
    this.setData({
      currentSwiperIndex: e.detail.current
    });
  },

  /**
   * 预览图片
   */
  previewImage: function (e) {
    const currentImg = e.currentTarget.dataset.img;
    if (this.data.goodsDetail && this.data.goodsDetail.images) {
      wx.previewImage({
        current: currentImg,
        urls: this.data.goodsDetail.images
      });
    }
  },

  /**
   * 切换标签页
   */
  switchTab: function (e) {
    const tab = e.currentTarget.dataset.tab;
    if (this.data.activeTab !== tab) {
      this.setData({
        activeTab: tab
      });
    }
  },

  /**
   * 选择规格
   */
  selectSpec: function (e) {
    const groupId = e.currentTarget.dataset.groupid;
    const optionId = e.currentTarget.dataset.optionid;

    if (!groupId || !optionId) {
      console.warn('规格选择参数缺失');
      return;
    }

    // 获取当前规格数据
    const specGroups = this.data.specGroups;
    const selectedSpecs = this.data.selectedSpecs;

    // 查找规格选项
    const option = this.findSpecOption(groupId, optionId);
    if (!option) {
      console.warn('未找到对应的规格选项');
      return;
    }

    // 检查选项是否可用
    if (option.disabled) {
      wx.showToast({
        title: '该规格暂不可用',
        icon: 'none',
        duration: 1500
      });
      return;
    }

    // 创建新的选中规格对象
    const newSelectedSpecs = JSON.parse(JSON.stringify(selectedSpecs));

    // 切换选中状态：如果已经选中则取消，否则选中
    if (newSelectedSpecs[groupId] === optionId) {
      delete newSelectedSpecs[groupId];
    } else {
      newSelectedSpecs[groupId] = optionId;
    }

    // 更新数据
    this.setData({
      selectedSpecs: newSelectedSpecs
    }, () => {
      // 更新规格组选中状态
      this.updateSpecGroupsSelection(newSelectedSpecs);
      // 计算价格
      this.calculatePrice(newSelectedSpecs);
    });
  },

  /**
   * 查找规格选项
   */
  findSpecOption: function (groupId, optionId) {
    if (!this.data.specGroups || !this.data.specGroups.length) {
      return null;
    }

    // 确保类型一致（dataset传递的是字符串）
    const groupIdNum = parseInt(groupId);
    const optionIdNum = parseInt(optionId);

    for (let i = 0; i < this.data.specGroups.length; i++) {
      const group = this.data.specGroups[i];
      if (group.id == groupIdNum) {
        if (group.options && group.options.length) {
          for (let j = 0; j < group.options.length; j++) {
            const option = group.options[j];
            if (option.id == optionIdNum) {
              return option;
            }
          }
        }
        break;
      }
    }
    return null;
  },

  /**
   * 计算价格
   */
  calculatePrice: function (selectedSpecs) {
    // 没有选择规格时显示基础价格
    if (Object.keys(selectedSpecs).length === 0) {
      const basePrice = this.data.goodsDetail ? this.data.goodsDetail.final_price : 0;
      this.setData({
        currentPrice: basePrice,
        selectedSku: null
      });
      return;
    }

    this.setData({
      isCalculatingPrice: true,
      priceCalculationError: false
    });

    const that = this;
    wx.request({
      url: api.calculatePrice,
      method: 'POST',
      data: {
        product_id: this.data.goodsId,
        selected_specs: selectedSpecs
      },
      success: function (res) {
        if (res.data.code === 200) {
          const priceData = res.data.data;
          that.setData({
            currentPrice: priceData.final_price,
            selectedSku: priceData.matched_sku ? {
              id: priceData.matched_sku,
              stock: priceData.stock
            } : null,
            isCalculatingPrice: false
          });
        } else {
          that.handlePriceCalculationError('价格计算失败');
        }
      },
      fail: function (err) {
        that.handlePriceCalculationError('网络请求失败');
      }
    });
  },

  /**
   * 处理价格计算错误
   */
  handlePriceCalculationError: function (message) {
    this.setData({
      priceCalculationError: true,
      isCalculatingPrice: false
    });
  },

  /**
   * 更新规格组选中状态
   */
  updateSpecGroupsSelection: function (selectedSpecs) {
    if (!this.data.specGroups || !this.data.specGroups.length) {
      return;
    }

    const specGroups = this.data.specGroups.map((group) => {
      const options = group.options.map((option) => {
        const isSelected = selectedSpecs[group.id] == option.id;
        return {
          ...option,
          selected: isSelected
        };
      });
      return {
        ...group,
        options: options
      };
    });

    this.setData({
      specGroups: specGroups
    });
  },

  /**
   * 获取选中的规格显示文本
   */
  getSelectedSpecValue: function () {
    const selectedSpecs = this.data.selectedSpecs;
    const specGroups = this.data.specGroups;

    if (!selectedSpecs || Object.keys(selectedSpecs).length === 0) {
      return '';
    }

    const specTexts = [];
    specGroups.forEach(function (group) {
      if (selectedSpecs[group.id]) {
        const selectedOption = group.options.find(function (opt) {
          return opt.id == selectedSpecs[group.id];
        });
        if (selectedOption) {
          specTexts.push(group.name + ': ' + selectedOption.value);
        }
      }
    });

    return specTexts.join(' ');
  },

  /**
   * 检查规格是否选择完整
   */
  isSpecSelectionComplete: function () {
    const selectedSpecs = this.data.selectedSpecs;
    const specGroups = this.data.specGroups;
    return Object.keys(selectedSpecs).length === specGroups.length;
  },

  /**
   * 检查是否缺货
   */
  isOutOfStock: function () {
    const selectedSku = this.data.selectedSku;
    const goodsDetail = this.data.goodsDetail;
    const stock = selectedSku ? selectedSku.stock : (goodsDetail ? goodsDetail.stock : 0);
    return stock === 0;
  },

  /**
   * 加载商品详情
   */
  loadGoodsDetail: function () {
    this.setData({
      loading: true,
      error: false
    });

    const that = this;

    return new Promise((resolve, reject) => {
      wx.request({
        url: api.productDetail + that.data.goodsId + '/',
        method: 'GET',
        success: function (res) {
          if (res.statusCode === 200 && res.data) {
            const goodsData = res.data;
            console.log('商品详情数据:', goodsData);

            // 处理图片数据
            const images = [goodsData.main_image].concat(goodsData.images || [])
              .filter(img => img && typeof img === 'string');

            const goodsDetail = {
              ...goodsData,
              images: images
            };

            // 初始化规格数据
            const specData = that.initSpecData(goodsDetail);

            that.setData({
              goodsDetail: goodsDetail,
              currentPrice: goodsData.final_price || goodsData.base_points_price || 0,
              ...specData,
              loading: false
            });

            // 初始价格计算
            that.calculatePrice(specData.selectedSpecs);

            console.log('商品详情加载完成，开始检查收藏状态');
            resolve(goodsDetail);
          } else {
            that.handleLoadError('商品数据加载失败');
            reject(new Error('商品数据加载失败'));
          }
        },
        fail: function (err) {
          that.handleLoadError('网络错误，请重试');
          reject(err);
        }
      });
    });
  },

  /**
   * 初始化规格数据
   */
  initSpecData: function (goodsDetail) {
    if (!goodsDetail.spec_groups || goodsDetail.spec_groups.length === 0) {
      return {
        specGroups: [],
        selectedSpecs: {},
        selectedSku: null
      };
    }

    // 处理规格组数据
    const specGroups = goodsDetail.spec_groups.map(function (group) {
      const options = (group.options || []).map(function (option) {
        return {
          ...option,
          selected: false,
          disabled: false
        };
      });
      return {
        ...group,
        options: options
      };
    });

    // 设置默认选中的规格
    let selectedSpecs = {};
    let selectedSku = null;

    // 尝试为每个规格组选择第一个可用选项
    specGroups.forEach(function (group) {
      const firstAvailable = group.options.find(function (opt) {
        return !opt.disabled;
      });
      if (firstAvailable) {
        selectedSpecs[group.id] = firstAvailable.id;
      }
    });

    return {
      specGroups: specGroups,
      selectedSpecs: selectedSpecs,
      selectedSku: selectedSku
    };
  },

  /**
   * 检查收藏状态（调用后端API）
   */
  checkFavoriteStatus: function () {
    // 检查用户是否登录
    if (!app.globalData.isLoggedIn) {
      console.log('用户未登录，收藏状态为false');
      this.setData({
        isFavorite: false,
        favoriteId: null
      });
      return;
    }

    // 避免重复检查
    if (this.data.isCheckingFavorite) {
      console.log('正在检查收藏状态，跳过');
      return;
    }

    this.setData({
      isCheckingFavorite: true
    });

    const that = this;
    wx.request({
      url: api.userFavorites,
      method: 'GET',
      header: {
        'Authorization': 'Bearer ' + app.globalData.token
      },
      data: {
        type: 'product',
        item_id: this.data.goodsId
      },
      success: function (res) {
        console.log('获取收藏状态响应:', res.data);
        console.log('完整的 results 结构:', JSON.stringify(res.data.results));

        that.setData({
          isCheckingFavorite: false
        });

        let isFavorite = false;
        let favoriteId = null;

        // 根据您的日志，数据结构为：{count: 1, next: null, previous: null, results: {...}}
        // 我们需要检查 results 对象的内容
        if (res.data && res.data.results) {
          const results = res.data.results;

          // 情况1: results 是对象，直接包含收藏信息
          if (results.code === 200 && results.data) {
            // 结构: {code: 200, message: "...", data: [...]}
            if (Array.isArray(results.data)) {
              const favorites = results.data;
              const favorite = favorites.find(item =>
                item.item_id == that.data.goodsId
              );
              if (favorite) {
                isFavorite = true;
                favoriteId = favorite.id;
              }
            }
          }
          // 情况2: results 直接是收藏记录对象
          else if (results.item_id == that.data.goodsId) {
            isFavorite = true;
            favoriteId = results.id;
            console.log('找到收藏记录:', results);
          }
          // 情况3: results 中包含 data 字段，且 data 是收藏记录
          else if (results.data && results.data.item_id == that.data.goodsId) {
            isFavorite = true;
            favoriteId = results.data.id;
          }
        }

        console.log('收藏状态检查结果:', {
          isFavorite,
          favoriteId,
          goodsId: that.data.goodsId
        });

        that.setData({
          isFavorite: isFavorite,
          favoriteId: favoriteId
        });

        // 更新缓存
        try {
          const favorites = wx.getStorageSync('userFavorites') || {};
          favorites[that.data.goodsId] = {
            isFavorite: isFavorite,
            favoriteId: favoriteId,
            timestamp: Date.now()
          };
          wx.setStorageSync('userFavorites', favorites);
          console.log('更新缓存成功');
        } catch (error) {
          console.error('更新收藏缓存失败:', error);
        }
      },
      fail: function (err) {
        console.error('获取收藏状态失败:', err);
        that.setData({
          isCheckingFavorite: false,
          isFavorite: false,
          favoriteId: null
        });
      }
    });
  },

  // 从服务器获取收藏状态
  fetchFavoriteStatusFromServer: function () {
    if (!app.globalData.isLoggedIn || this.data.isCheckingFavorite) return;

    this.setData({
      isCheckingFavorite: true
    });

    const that = this;
    wx.request({
      url: api.userFavorites,
      method: 'GET',
      header: {
        'Authorization': 'Bearer ' + app.globalData.token
      },
      data: {
        type: 'product',
        item_id: this.data.goodsId
      },
      success: function (res) {
        console.log('获取收藏状态响应:', res.data);
        console.log('results 内容:', res.data.results);
        console.log('results 类型:', typeof res.data.results);
        console.log('results 是否为数组:', Array.isArray(res.data.results));

        that.setData({
          isCheckingFavorite: false
        });

        let isFavorite = false;
        let favoriteId = null;

        // 处理响应数据
        if (res.data) {
          // 检查分页结构：{count: X, next: null, previous: null, results: {...}}
          if (res.data.results) {
            const results = res.data.results;

            // 情况1: results 是一个对象，包含收藏信息
            if (typeof results === 'object' && !Array.isArray(results)) {
              console.log('results 是一个对象:', results);

              // 检查对象是否包含收藏数据
              if (results.code === 200 && results.data) {
                // 结构: {code: 200, message: "...", data: [...]}
                if (Array.isArray(results.data)) {
                  const favorites = results.data;
                  const favorite = favorites.find(item =>
                    item.item_id === that.data.goodsId
                  );
                  if (favorite) {
                    isFavorite = true;
                    favoriteId = favorite.id;
                  }
                }
                // 结构: {code: 200, message: "...", data: {is_favorite: true, favorite_id: 123}}
                else if (results.data.is_favorite !== undefined) {
                  isFavorite = results.data.is_favorite;
                  favoriteId = results.data.favorite_id || null;
                }
              }
              // 如果 results 对象直接包含收藏记录
              else if (results.item_id === that.data.goodsId) {
                isFavorite = true;
                favoriteId = results.id;
              }
              // 如果 results 对象包含 data 字段，且 data 是收藏记录
              else if (results.data && results.data.item_id === that.data.goodsId) {
                isFavorite = true;
                favoriteId = results.data.id;
              }
            }
            // 情况2: results 是数组
            else if (Array.isArray(res.data.results)) {
              const favorites = res.data.results;
              const favorite = favorites.find(item =>
                item.item_id === that.data.goodsId
              );
              if (favorite) {
                isFavorite = true;
                favoriteId = favorite.id;
              }
            }
          }
          // 其他结构...
          else if (res.data.code === 200 && Array.isArray(res.data.data)) {
            const favorites = res.data.data;
            const favorite = favorites.find(item =>
              item.item_id === that.data.goodsId
            );
            if (favorite) {
              isFavorite = true;
              favoriteId = favorite.id;
            }
          }
          // 直接返回数组的情况
          else if (Array.isArray(res.data)) {
            const favorite = res.data.find(item =>
              item.item_id === that.data.goodsId
            );
            if (favorite) {
              isFavorite = true;
              favoriteId = favorite.id;
            }
          }
        }

        console.log('收藏状态检查结果:', {
          isFavorite,
          favoriteId,
          goodsId: that.data.goodsId,
          responseData: res.data
        });

        that.setData({
          isFavorite: isFavorite,
          favoriteId: favoriteId
        });

        // 更新缓存
        try {
          const favorites = wx.getStorageSync('userFavorites') || {};
          favorites[that.data.goodsId] = {
            isFavorite: isFavorite,
            timestamp: Date.now()
          };
          wx.setStorageSync('userFavorites', favorites);
        } catch (error) {
          console.error('更新收藏缓存失败:', error);
        }
      },
      fail: function (err) {
        console.error('获取收藏状态失败:', err);
        that.setData({
          isCheckingFavorite: false,
          isFavorite: false,
          favoriteId: null
        });
      }
    });
  },

  // 添加一个调试函数来查看完整的API响应
  debugAPIResponse: function () {
    console.log('=== 开始调试收藏API ===');
    console.log('商品ID:', this.data.goodsId);
    console.log('用户Token:', app.globalData.token ? '存在' : '不存在');

    wx.request({
      url: api.userFavorites,
      method: 'GET',
      header: {
        'Authorization': 'Bearer ' + app.globalData.token
      },
      data: {
        type: 'product',
        item_id: this.data.goodsId
      },
      success: (res) => {
        console.log('完整的API响应:');
        console.log('状态码:', res.statusCode);
        console.log('响应头:', res.header);
        console.log('原始响应数据:', res.data);

        // 深度遍历对象，查看所有属性
        function logObject(obj, indent = '') {
          for (let key in obj) {
            if (obj.hasOwnProperty(key)) {
              console.log(indent + key + ':', obj[key]);
              if (typeof obj[key] === 'object' && obj[key] !== null) {
                logObject(obj[key], indent + '  ');
              }
            }
          }
        }

        console.log('响应数据分解:');
        logObject(res.data);

        // 显示在页面上
        wx.showModal({
          title: 'API响应调试',
          content: JSON.stringify(res.data, null, 2),
          showCancel: false
        });
      },
      fail: (err) => {
        console.error('调试请求失败:', err);
      }
    });
  },

  // 从服务器获取收藏ID（用于缓存中已有收藏状态但缺少ID的情况）
  fetchFavoriteIdFromServer: function () {
    if (!app.globalData.isLoggedIn || this.data.isCheckingFavorite) return;

    this.setData({
      isCheckingFavorite: true
    });

    const that = this;
    wx.request({
      url: api.userFavorites,
      method: 'GET',
      header: {
        'Authorization': 'Bearer ' + app.globalData.token
      },
      data: {
        type: 'product',
        item_id: this.data.goodsId
      },
      success: function (res) {
        console.log('获取收藏ID响应:', res.data);
        that.setData({
          isCheckingFavorite: false
        });

        // 解析收藏ID
        let favoriteId = null;
        if (res.data?.code === 200 && Array.isArray(res.data.data)) {
          const favorite = res.data.data.find(item =>
            item.item_id === that.data.goodsId
          );
          if (favorite) {
            favoriteId = favorite.id;
          }
        }

        if (favoriteId) {
          that.setData({
            favoriteId: favoriteId
          });
        }
      },
      fail: function (err) {
        console.error('获取收藏ID失败:', err);
        that.setData({
          isCheckingFavorite: false
        });
      }
    });
  },


  /**
   * 切换收藏状态（调用后端API）
   */
  toggleFavorite: function () {
    console.log('切换收藏，当前状态:', this.data.isFavorite, '收藏ID:', this.data.favoriteId);

    // 检查用户是否登录
    if (!app.globalData.isLoggedIn) {
      wx.showToast({
        title: '请先登录',
        icon: 'none',
        duration: 1500
      });

      setTimeout(() => {
        wx.navigateTo({
          url: '/pages/user/login/login?redirect=/pages/mall/goodsdetail/goodsdetail?id=' + this.data.goodsId
        });
      }, 500);
      return;
    }

    const that = this;
    const isFavorite = this.data.isFavorite;
    const favoriteId = this.data.favoriteId;
    const goodsDetail = this.data.goodsDetail;

    if (isFavorite) {
      // 取消收藏
      this.cancelFavorite(favoriteId);
    } else {
      // 添加收藏
      this.addFavorite(goodsDetail);
    }
  },

  // 添加收藏
  addFavorite: function (goodsDetail) {
    const requestData = {
      favorite_type: 'product',
      item_id: this.data.goodsId,
      item_name: goodsDetail.name || '商品',
      item_image: goodsDetail.main_image || '',
      item_url: ''
    };

    console.log('添加收藏请求数据:', requestData);

    wx.request({
      url: api.userFavoriteCreate,
      method: 'POST',
      header: {
        'Authorization': 'Bearer ' + app.globalData.token,
        'Content-Type': 'application/json'
      },
      data: requestData,
      success: (res) => {
        console.log('添加收藏响应:', res.data);

        // 处理成功响应（200或201）
        if (res.statusCode === 200 || res.statusCode === 201 ||
          (res.data && (res.data.code === 200 || res.data.code === 201))) {
          wx.showToast({
            title: res.data?.message || '收藏成功',
            icon: 'success',
            duration: 1500
          });

          // 更新收藏状态
          let favoriteId = null;
          if (res.data && res.data.data && res.data.data.id) {
            favoriteId = res.data.data.id;
          } else if (res.data && res.data.data && res.data.data.favorite_id) {
            favoriteId = res.data.data.favorite_id;
          }

          this.setData({
            isFavorite: true,
            favoriteId: favoriteId
          });

          // 保存到缓存
          this.saveFavoriteToCache();
        } else {
          wx.showToast({
            title: res.data?.message || '收藏失败',
            icon: 'none',
            duration: 1500
          });
        }
      },
      fail: (err) => {
        console.error('收藏请求失败:', err);
        wx.showToast({
          title: '网络错误',
          icon: 'none',
          duration: 1500
        });
      }
    });
  },

// 取消收藏 
cancelFavorite: function(favoriteId) {
  console.log('开始取消收藏，收藏ID:', favoriteId);
  
  // 如果没有收藏ID，尝试从缓存中获取
  if (!favoriteId) {
    try {
      const favorites = wx.getStorageSync('userFavorites') || {};
      const cached = favorites[this.data.goodsId];
      if (cached && cached.favoriteId) {
        favoriteId = cached.favoriteId;
        console.log('从缓存获取收藏ID:', favoriteId);
      }
    } catch (error) {
      console.error('从缓存获取收藏ID失败:', error);
    }
  }
  
  if (!favoriteId) {
    wx.showToast({
      title: '无法获取收藏记录',
      icon: 'none',
      duration: 1500
    });
    return;
  }
  
  wx.request({
    url: api.userFavoriteDetail + favoriteId + '/',
    method: 'DELETE',
    header: {
      'Authorization': 'Bearer ' + app.globalData.token,
      'Content-Type': 'application/json'
    },
    success: (res) => {
      console.log('取消收藏响应:', res.data);
      console.log('响应状态码:', res.statusCode);
      
      // 处理成功响应
      if (res.statusCode === 200 || res.statusCode === 204 || 
          (res.data && res.data.code === 200)) {
        
        // 更新前端状态
        this.setData({
          isFavorite: false,
          favoriteId: null
        });
        
        // 更新缓存
        try {
          const favorites = wx.getStorageSync('userFavorites') || {};
          delete favorites[this.data.goodsId];
          wx.setStorageSync('userFavorites', favorites);
          console.log('从缓存删除收藏成功');
        } catch (error) {
          console.error('从缓存删除收藏失败:', error);
        }
        
        wx.showToast({
          title: '已取消收藏',
          icon: 'success',
          duration: 1500
        });
        
        // 触发事件，通知其他页面（如收藏列表页）更新
        if (app.globalData.eventBus) {
          app.globalData.eventBus.emit('favoriteChanged', {
            goodsId: this.data.goodsId,
            isFavorite: false
          });
        }
      } else {
        wx.showToast({
          title: res.data?.message || '取消收藏失败',
          icon: 'none',
          duration: 1500
        });
      }
    },
    fail: (err) => {
      console.error('取消收藏请求失败:', err);
      wx.showToast({
        title: '网络错误',
        icon: 'none',
        duration: 1500
      });
    }
  });
},

  // 保存收藏到缓存
  saveFavoriteToCache: function () {
    try {
      const favorites = wx.getStorageSync('userFavorites') || {};
      favorites[this.data.goodsId] = {
        isFavorite: true,
        timestamp: Date.now()
      };
      wx.setStorageSync('userFavorites', favorites);
    } catch (error) {
      console.error('保存收藏到缓存失败:', error);
    }
  },

  // 从缓存移除收藏
  removeFavoriteFromCache: function () {
    try {
      const favorites = wx.getStorageSync('userFavorites') || {};
      delete favorites[this.data.goodsId];
      wx.setStorageSync('userFavorites', favorites);
    } catch (error) {
      console.error('从缓存移除收藏失败:', error);
    }
  },

  /**
   * 获取购物车数量
   */
  getCartCount: function () {
    try {
      const cart = wx.getStorageSync('cartData') || [];
      const count = cart.reduce(function (total, item) {
        return total + (item.quantity || 0);
      }, 0);
      this.setData({
        cartCount: count
      });
    } catch (error) {
      console.error('获取购物车数量失败:', error);
    }
  },

  /**
   * 加入购物车（显示弹窗）
   */
  addToCartWithAnimation: function () {
    if (!this.data.goodsDetail) {
      wx.showToast({
        title: '商品信息加载中',
        icon: 'none',
        duration: 1500
      });
      return;
    }

    // 检查是否有规格需要选择
    if (this.data.specGroups.length > 0) {
      this.showBuyPopup('addCart');
    } else {
      // 无规格商品直接加入购物车
      this.addToCart();
    }
  },

  /**
   * 显示购买弹窗
   */
  showBuyPopup: function (popupType) {
    this.setData({
      buyPopupVisible: true,
      popupType: popupType
    });
  },

  /**
   * 确认加入购物车
   */
  confirmAddCart: function () {
    if (!this.isSpecSelectionComplete() && this.data.specGroups.length > 0) {
      wx.showToast({
        title: '请先选择完整规格',
        icon: 'none',
        duration: 1500
      });
      return;
    }

    if (this.isOutOfStock()) {
      wx.showToast({
        title: '商品已售罄',
        icon: 'none',
        duration: 1500
      });
      return;
    }

    this.addToCart();
    this.closeBuyPopup();
  },

  /**
   * 加入购物车逻辑
   */
  addToCart: function () {
    if (!this.data.goodsDetail) return;

    const goodsDetail = this.data.goodsDetail;
    const selectedSku = this.data.selectedSku;
    const currentPrice = this.data.currentPrice;
    const selectedSpecs = this.data.selectedSpecs;

    // 构建购物车商品项
    const cartItem = {
      id: goodsDetail.id,
      skuId: selectedSku ? selectedSku.id : null,
      title: goodsDetail.name,
      image: selectedSku ? (selectedSku.image || goodsDetail.main_image) : goodsDetail.main_image,
      price: currentPrice,
      spec: this.getSelectedSpecValue(),
      selectedSpecs: selectedSpecs,
      quantity: 1,
      type: 'virtual',
      maxStock: selectedSku ? selectedSku.stock : goodsDetail.stock
    };

    try {
      let cart = wx.getStorageSync('cartData') || [];
      const existingIndex = cart.findIndex(function (item) {
        return item.id === cartItem.id &&
          item.skuId === cartItem.skuId &&
          JSON.stringify(item.selectedSpecs) === JSON.stringify(cartItem.selectedSpecs);
      });

      if (existingIndex > -1) {
        // 检查库存是否足够
        if (cart[existingIndex].quantity >= cart[existingIndex].maxStock) {
          wx.showToast({
            title: '库存不足',
            icon: 'none',
            duration: 1500
          });
          return;
        }
        cart[existingIndex].quantity += 1;
      } else {
        cart.push(cartItem);
      }

      wx.setStorageSync('cartData', cart);
      this.getCartCount();

      wx.showToast({
        title: '已加入购物车',
        icon: 'success',
        duration: 1500
      });
    } catch (error) {
      console.error('加入购物车失败:', error);
      wx.showToast({
        title: '加入购物车失败',
        icon: 'none',
        duration: 1500
      });
    }
  },

  /**
   * 立即购买
   */
  buyNow: function () {
    if (!this.data.goodsDetail) {
      wx.showToast({
        title: '商品信息加载中',
        icon: 'none',
        duration: 1500
      });
      return;
    }

    // 检查是否有规格需要选择
    if (this.data.specGroups.length > 0) {
      this.showBuyPopup('buyNow');
    } else {
      // 无规格商品直接购买
      this.confirmBuy();
    }
  },

  /**
   * 关闭购买弹窗
   */
  closeBuyPopup: function () {
    this.setData({
      buyPopupVisible: false
    });
  },

  /**
   * 确认购买
   */
  confirmBuy: function () {
    if (!this.isSpecSelectionComplete() && this.data.specGroups.length > 0) {
      wx.showToast({
        title: '请先选择完整规格',
        icon: 'none',
        duration: 1500
      });
      return;
    }

    if (this.isOutOfStock()) {
      wx.showToast({
        title: '商品已售罄',
        icon: 'none',
        duration: 1500
      });
      return;
    }

    const goodsDetail = this.data.goodsDetail;
    const selectedSku = this.data.selectedSku;
    const currentPrice = this.data.currentPrice;
    const selectedSpecs = this.data.selectedSpecs;

    // 构建订单数据
    const orderData = {
      goodsId: goodsDetail.id,
      skuId: selectedSku ? selectedSku.id : null,
      goodsName: goodsDetail.name,
      image: selectedSku ? (selectedSku.image || goodsDetail.main_image) : goodsDetail.main_image,
      price: currentPrice,
      spec: this.getSelectedSpecValue(),
      selectedSpecs: selectedSpecs,
      quantity: 1,
      type: 'virtual'
    };

    // 跳转到确认订单页面
    wx.navigateTo({
      url: '/pages/mall/order/confirm/confirm?data=' + encodeURIComponent(JSON.stringify(orderData))
    });

    this.closeBuyPopup();
  },

  /**
   * 跳转到购物车
   */
  goToCart: function () {
    wx.navigateTo({
      url: '/pages/mall/cart/cart'
    });
  },

  /**
   * 用户点击右上角分享
   */
  onShareAppMessage: function () {
    const goodsDetail = this.data.goodsDetail;
    const goodsId = this.data.goodsId;
    return {
      title: goodsDetail ? goodsDetail.name : '积分商城好物',
      path: '/pages/mall/goodsdetail/goodsdetail?id=' + goodsId,
      imageUrl: goodsDetail ? goodsDetail.main_image : ''
    };
  },

  /**
   * 页面相关事件处理函数--监听用户下拉动作
   */
  onPullDownRefresh: function () {
    this.loadGoodsDetail().then(() => {
      wx.stopPullDownRefresh();
    });
  },

  /**
   * 页面上拉触底事件的处理函数
   */
  onReachBottom: function () {
    // 可以在这里加载更多评论等
  }
});