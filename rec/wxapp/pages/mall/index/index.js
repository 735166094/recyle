const app = getApp();
const api = require('../../../config/settings');
Page({
  /**
   * 页面的初始数据
   */
  data: {
    isCategoryPage: false, // 控制显示首页还是分类页
    inputValue: '',
    activeList: [], // 初始默认数据（活动轮播图）
    goodList: [], // 热商城首页需要加载的热门商品

    // 分类商品数据
    categoryGoodsMap: {}, // 存储各个分类的商品数据
    currentCategoryGoods: [], // 当前激活分类的商品列表

    // 分页相关数据
    pagination: {
      page: 1,
      pageSize: 5, // 每次加载5个商品
      hasMore: true,
      isLoading: false
    },
    // 防止快速点击导致的闪屏
    isAddingToCart: false,
    activeCategoryName: '', // 分类数据
    categories: [],
    displayCategories: [], //商城首页快捷入口分类
    activeCategoryId: 1,
    categoryGoods: [], // 分类商品
    cart: [],
    cartBadgeCount: 0, // 购物车悬浮窗数量徽章

    // 购物车弹窗相关数据
    addCartPopupVisible: false, // 控制弹窗显示
    popupGoodsDetail: null, // 弹窗商品详情
    specGroups: [], // 规格组
    selectedSpecs: {}, // 选中的规格
    selectedSku: null, // 选中的SKU
    currentPrice: 0, // 当前价格
    isCalculatingPrice: false, // 是否正在计算价格
    priceCalculationError: false, // 价格计算错误

    // 搜索相关数据
    isSearching: false, // 是否正在搜索
    searchResults: [], // 搜索结果
    searchKeyword: '', // 搜索关键词
    searchPagination: {
      page: 1,
      pageSize: 10,
      hasMore: true,
      isLoading: false
    },

  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    // 初始化时先设置空数组，避免undefined
    this.setData({
      activeList: [],
      goodList: [],
      categories: [],
      displayCategories: []
    });

    // 初始化时设置默认分类名称
    const defaultCategory = this.data.categories.find(cat => cat.id === this.data.activeCategoryId);
    this.setData({
      activeCategoryName: defaultCategory ? defaultCategory.name : ''
    });

    // 初始化购物车悬浮窗数量
    this.updateCartBadge();

    // 获取轮播图数据
    this.getBannerData();

    // 获取热门商品数据
    this.getHotGoodsData(1);

    // 获取分类数据
    this.getCategoriesData();
  },

  /**
   * 生命周期函数--监听页面显示
   */
  onShow() {
    // 页面显示时更新购物车悬浮窗数量
    this.updateCartBadge();
  },

  /**
   * 获取分类数据
   */
  getCategoriesData() {
    const that = this;
    wx.request({
      url: api.mallcategories,
      method: 'GET',
      success(res) {
        if (res.statusCode === 200) {
          const responseData = res.data;

          // 检查不同的响应格式
          let categoryList = [];

          if (responseData.code === 200 && responseData.data && responseData.data.results) {
            // 格式1: {code: 200, data: {results: [...], count: ...}}
            categoryList = responseData.data.results;
          } else if (responseData.results) {
            // 格式2: {results: [...], count: ...}
            categoryList = responseData.results;
          } else if (Array.isArray(responseData)) {
            // 格式3: 直接返回数组
            categoryList = responseData;
          } else {
            console.error('未知的响应格式:', responseData);
            that.setData({
              categories: [],
              displayCategories: []
            });
            wx.showToast({
              title: '分类数据格式错误',
              icon: 'none'
            });
            return;
          }

          // 映射数据格式，将接口返回的数据转换为前端需要的格式
          const categories = categoryList.map(item => {
            return {
              id: item.id,
              name: item.name,
              icon: item.icon || '', // 使用后端返回的icon，如果没有则为空
              image: item.image || '', // 保存图片URL备用
              description: item.description,
              product_count: item.product_count,
              is_active: item.is_active
            };
          });

          // 设置所有分类数据
          that.setData({
            categories: categories
          });

          // 设置首页快捷入口显示的分类（取前4个）
          that.setData({
            displayCategories: categories.slice(0, 4)
          });

          // 如果当前激活的分类不在新数据中，重置为第一个分类
          const currentCategoryExists = categories.find(cat => cat.id === that.data.activeCategoryId);
          if (!currentCategoryExists && categories.length > 0) {
            that.setData({
              activeCategoryId: categories[0].id,
              activeCategoryName: categories[0].name
            });
          }
        } else {
          console.error('获取分类数据失败', res);
          // 如果接口失败，使用空数组，避免页面报错
          that.setData({
            categories: [],
            displayCategories: []
          });
          wx.showToast({
            title: '分类数据加载失败',
            icon: 'none'
          });
        }
      },
      fail(err) {
        console.error('分类接口请求失败', err);
        // 如果接口失败，使用空数组，避免页面报错
        that.setData({
          categories: [],
          displayCategories: []
        });
        wx.showToast({
          title: '分类数据加载失败',
          icon: 'none'
        });
      }
    });
  },

  /**
   * 获取轮播图数据
   */
  getBannerData() {
    const that = this;
    wx.request({
      url: api.banners,
      method: 'GET',
      success(res) {
        if (res.statusCode === 200) {
          const responseData = res.data;
          console.log('轮播图响应数据:', responseData); // 添加调试日志

          // 检查不同的响应格式
          let bannerList = [];

          if (responseData.code === 200 && responseData.data && responseData.data.results) {
            // 格式1: {code: 200, data: {results: [...], count: ...}}
            bannerList = responseData.data.results;
          } else if (responseData.results) {
            // 格式2: {results: [...], count: ...}
            bannerList = responseData.results;
          } else if (Array.isArray(responseData)) {
            // 格式3: 直接返回数组
            bannerList = responseData;
          }

          console.log('处理后的轮播图数据:', bannerList); // 添加调试日志

          // 如果有数据才映射格式
          if (bannerList && bannerList.length > 0) {
            // 映射数据格式，将接口返回的数据转换为 banner 组件需要的格式
            const activeList = bannerList.map(item => {
              return {
                id: item.id,
                title: item.title,
                image: item.image,
                desc: item.desc,
                link: item.target_url,
                type: item.type
              };
            });
            that.setData({
              activeList: activeList
            });
          }
        }
      },
    });
  },

  /**
   * 获取热门商品数据
   */
  getHotGoodsData(page = 1) {
    // 防止重复请求
    if (this.data.pagination.isLoading) return;

    this.setData({
      'pagination.isLoading': true,
      'pagination.page': page
    });

    const that = this;
    wx.request({
      url: api.hotgoods + `?page=${page}&page_size=5`,
      method: 'GET',
      success(res) {
        if (res.statusCode === 200) {
          const responseData = res.data;

          // 检查不同的响应格式
          let goodsList = [];

          if (responseData.code === 200 && responseData.data && responseData.data.results) {
            // 格式1: {code: 200, data: {results: [...], count: ...}}
            goodsList = responseData.data.results;
          } else if (responseData.results) {
            // 格式2: {results: [...], count: ...}
            goodsList = responseData.results;
          } else if (Array.isArray(responseData)) {
            // 格式3: 直接返回数组
            goodsList = responseData;
          } else {
            console.error('未知的响应格式:', responseData);
            that.setData({
              'pagination.isLoading': false
            });
            wx.showToast({
              title: '商品数据格式错误',
              icon: 'none'
            });
            return;
          }

          // 映射数据格式，将接口返回的数据转换为前端需要的格式
          const newGoodsList = goodsList.map(item => {
            // 根据商品属性确定类型标签
            let type = "";
            if (item.is_hot) {
              type = "热销";
            } else if (item.is_new) {
              type = "新品";
            } else if (item.discount_percent > 0) {
              type = "特惠";
            }

            return {
              id: item.id,
              imgUrl: item.main_image,
              type: type,
              title: item.name,
              currency: "iconfont icon-point", 
              price: item.final_price, // 使用最终价格
              originalPrice: item.original_points, // 原价（积分）
              pointsPrice: item.points_price, // 积分价格
              discountPercent: item.discount_percent, // 折扣百分比
              isOnSale: item.is_on_sale,
              stock: item.stock,
              salesCount: item.sales_count,
              categoryName: item.category_name,
              rating: item.rating,
              reviewCount: item.review_count
            };
          });

          // 判断是否是第一页
          if (page === 1) {
            that.setData({
              goodList: newGoodsList
            });
          } else {
            // 追加数据
            that.setData({
              goodList: [...that.data.goodList, ...newGoodsList]
            });
          }

          // 更新分页状态
          const hasMore = (responseData.next !== null && responseData.next !== undefined) ||
            (responseData.data && responseData.data.next !== null && responseData.data.next !== undefined);
          that.setData({
            'pagination.hasMore': hasMore,
            'pagination.isLoading': false
          });

          // 如果没有更多数据，显示提示
          if (!hasMore && page > 1) {
            wx.showToast({
              title: '没有更多商品了',
              icon: 'none',
              duration: 1500
            });
          }
        } else {
          console.error('获取热门商品数据失败', res);
          that.setData({
            'pagination.isLoading': false
          });
          wx.showToast({
            title: '商品加载失败',
            icon: 'none'
          });
        }
      },
      fail(err) {
        console.error('热门商品接口请求失败', err);
        that.setData({
          'pagination.isLoading': false
        });
        wx.showToast({
          title: '网络错误，请重试',
          icon: 'none'
        });
      }
    });
  },

  /**
   * 加载更多商品
   */
  loadMoreGoods() {
    if (this.data.pagination.hasMore && !this.data.pagination.isLoading) {
      const nextPage = this.data.pagination.page + 1;
      this.getHotGoodsData(nextPage);
    }
  },

  /**
   * 生命周期函数--监听页面显示
   */
  onShow() {
    // 页面显示时更新购物车悬浮窗数量
    this.updateCartBadge();
  },

  // 显示加入购物车弹窗
  showAddCartPopup(e) {
    const goodId = e.currentTarget.dataset.id;
    let goods = null;

    // 查找商品信息
    const currentCategoryGoodsList = this.data.categoryGoods[this.data.activeCategoryId] || [];
    goods = currentCategoryGoodsList.find(item => item.id === goodId);

    if (!goods) {
      goods = this.data.goodList.find(item => item.id === goodId);
    }

    if (goods) {
      // 显示弹窗并设置商品信息
      this.setData({
        addCartPopupVisible: true,
        popupGoodsDetail: goods,
        currentPrice: goods.price || 0,
        specGroups: [], // 清空之前的规格
        selectedSpecs: {}, // 清空选中的规格
        selectedSku: null // 清空选中的SKU
      });

      // 获取商品规格信息（如果有）
      this.getGoodsSpecifications(goodId);

      // 显示加载状态
      wx.showLoading({
        title: '加载中...',
      });
    }
  },

  // 获取商品规格信息
  getGoodsSpecifications(goodId) {
    const that = this;
    wx.request({
      url: api.productDetail + goodId + '/',
      method: 'GET',
      success(res) {
        wx.hideLoading();

        if (res.statusCode === 200 && res.data) {
          const goodsData = res.data;

          // 更新弹窗中的商品详情为完整数据
          that.setData({
            popupGoodsDetail: goodsData,
            currentPrice: goodsData.final_price || goodsData.base_points_price || 0
          });

          // 如果有规格信息，初始化规格数据
          if (goodsData.spec_groups && goodsData.spec_groups.length > 0) {
            const specData = that.initSpecData(goodsData);
            that.setData({
              ...specData
            });

            // 如果有默认选中的规格，计算价格
            if (Object.keys(specData.selectedSpecs).length > 0) {
              that.calculatePriceForSelectedSpecs(specData.selectedSpecs);
              that.updateSelectedSku(specData.selectedSpecs);
            }
          } else {
            // 没有规格信息，清空规格数据
            that.setData({
              specGroups: [],
              selectedSpecs: {},
              selectedSku: null
            });
          }
        }
      },
      fail(err) {
        wx.hideLoading();
        console.error('获取商品规格失败', err);
        // 获取失败时清空规格数据
        that.setData({
          specGroups: [],
          selectedSpecs: {},
          selectedSku: null
        });
      }
    });
  },

  // 初始化规格数据
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

  // 选择规格
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

    // 设置选中状态：同一规格组只能选中一个，所以直接覆盖
    newSelectedSpecs[groupId] = optionId;

    console.log('选择规格:', {
      groupId: groupId,
      optionId: optionId,
      selectedSpecs: newSelectedSpecs
    });

    // 更新数据
    this.setData({
      selectedSpecs: newSelectedSpecs
    }, () => {
      // 更新规格组选中状态
      this.updateSpecGroupsSelection(newSelectedSpecs);

      // 计算价格
      this.calculatePriceForSelectedSpecs(newSelectedSpecs);

      // 更新选中的SKU
      this.updateSelectedSku(newSelectedSpecs);

      // 调试：打印当前状态
      console.log('规格选择完整性:', this.isSpecSelectionComplete());
      console.log('库存状态:', this.isOutOfStock());
      console.log('选中的规格:', newSelectedSpecs);
    });
  },

  // 查找规格选项
  findSpecOption: function (groupId, optionId) {
    if (!this.data.specGroups || !this.data.specGroups.length) {
      return null;
    }

    // 确保类型一致
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

  // 更新规格组选中状态
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

  // 获取选中的规格显示文本
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

  // 直接加入购物车
  addToCartDirectly() {
    const goods = this.data.popupGoodsDetail;
    const selectedSpecs = this.data.selectedSpecs || {};

    console.log('直接加入购物车参数:', {
      goodsId: goods ? goods.id : 'null',
      goods: goods,
      selectedSpecs: selectedSpecs,
      selectedSku: this.data.selectedSku
    });

    if (!goods) {
      wx.showToast({
        title: '商品信息加载失败',
        icon: 'none',
        duration: 1500
      });
      return;
    }

    // 检查库存
    if (this.isOutOfStock()) {
      wx.showToast({
        title: '商品已售罄',
        icon: 'none',
        duration: 1500
      });
      return;
    }

    // 如果有选中的SKU，使用SKU信息
    if (this.data.selectedSku) {
      console.log('使用选中的SKU:', this.data.selectedSku);
    }

    // 调用加入购物车函数
    this.addToCart(goods, selectedSpecs);
  },

  // 计算选中规格的价格
  calculatePriceForSelectedSpecs: function (selectedSpecs) {
    const specGroups = this.data.specGroups;
    const popupGoodsDetail = this.data.popupGoodsDetail;

    if (!specGroups || specGroups.length === 0 || !popupGoodsDetail) {
      return;
    }

    let basePrice = popupGoodsDetail.final_price || popupGoodsDetail.price || 0;
    let totalPrice = basePrice;

    // 遍历所有规格组，累加选中的规格选项的价格调整
    specGroups.forEach(group => {
      if (selectedSpecs[group.id]) {
        const selectedOption = group.options.find(opt => opt.id == selectedSpecs[group.id]);
        if (selectedOption && selectedOption.price_increment) {
          totalPrice += selectedOption.price_increment;
        }
      }
    });

    this.setData({
      currentPrice: totalPrice
    });
  },

  // 更新选中的SKU
  updateSelectedSku: function (selectedSpecs) {
    const popupGoodsDetail = this.data.popupGoodsDetail;
    if (!popupGoodsDetail || !popupGoodsDetail.skus) {
      this.setData({
        selectedSku: null
      });
      return;
    }

    // 如果所有规格都选择了，查找匹配的SKU
    if (Object.keys(selectedSpecs).length === this.data.specGroups.length) {
      const selectedOptionIds = Object.values(selectedSpecs).map(id => parseInt(id));

      for (const sku of popupGoodsDetail.skus) {
        if (sku.spec_options) {
          const skuOptionIds = sku.spec_options.map(opt => opt.id);
          // 比较两个数组是否包含相同的元素
          if (selectedOptionIds.length === skuOptionIds.length &&
            selectedOptionIds.every(id => skuOptionIds.includes(id))) {
            this.setData({
              selectedSku: sku
            });
            return;
          }
        }
      }
    }

    // 如果没有找到匹配的SKU，设置为null
    this.setData({
      selectedSku: null
    });
  },

  /**
   * 检查是否缺货
   */
  isOutOfStock: function () {
    const popupGoodsDetail = this.data.popupGoodsDetail;
    const selectedSku = this.data.selectedSku;

    // 如果有选中的SKU，使用SKU的库存
    if (selectedSku) {
      return selectedSku.stock === 0 || selectedSku.stock < 1;
    }

    // 如果没有选中的SKU但有商品详情，使用商品的库存
    if (popupGoodsDetail) {
      return popupGoodsDetail.stock === 0 || popupGoodsDetail.stock < 1;
    }

    return true; // 默认缺货
  },

  /**
   * 检查规格是否选择完整
   */
  isSpecSelectionComplete: function () {
    /**
     * 检查规格选择是否完整
     * @returns {boolean} 如果所有规格组都已选择则返回true，否则返回false
     * @description 该方法会检查已选规格数量是否等于规格组数量，如果没有规格组则直接返回true
     */
    const selectedSpecs = this.data.selectedSpecs;
    const specGroups = this.data.specGroups;

    console.log('检查规格完整性:', {
      selectedSpecsCount: Object.keys(selectedSpecs).length,
      specGroupsCount: specGroups.length,
      selectedSpecs: selectedSpecs,
      specGroups: specGroups.map(g => ({
        id: g.id,
        name: g.name
      }))
    });

    // 如果没有规格组，则认为是完整的
    if (!specGroups || specGroups.length === 0) {
      return true;
    }

    const isComplete = Object.keys(selectedSpecs).length === specGroups.length;
    console.log('规格完整性结果:', isComplete);

    return isComplete;
  },

  /**
   * 获取选中规格的显示文本
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

  // 关闭加入购物车弹窗
  closeAddCartPopup() {
    this.setData({
      addCartPopupVisible: false,
      specGroups: [],
      selectedSpecs: {},
      selectedSku: null
    });
  },

  // 确认加入购物车
  confirmAddToCart(e) {
    console.log('确认加入购物车按钮被点击');

    // 首先检查规格是否选择完整
    if (!this.isSpecSelectionComplete()) {
      console.log('规格选择不完整，当前选中的规格:', this.data.selectedSpecs);
      console.log('规格组数量:', this.data.specGroups.length);

      wx.showToast({
        title: '请先选择完整规格',
        icon: 'none',
        duration: 1500
      });
      return;
    }

    // 检查库存
    if (this.isOutOfStock()) {
      console.log('商品缺货，SKU库存:', this.data.selectedSku ? this.data.selectedSku.stock : 'null');

      wx.showToast({
        title: '商品已售罄',
        icon: 'none',
        duration: 1500
      });
      return;
    }

    console.log('加入购物车条件满足，开始加入...', {
      goods: this.data.popupGoodsDetail,
      selectedSpecs: this.data.selectedSpecs,
      selectedSku: this.data.selectedSku
    });

    // 直接调用加入购物车逻辑
    this.addToCartDirectly();

    // 注意：不要在这里调用 closeAddCartPopup()，
    // 因为 addToCartDirectly 中成功后会自己关闭弹窗
  },

  // 加入购物车
  addToCart(goods, selectedSpecs = {}) {
    console.log('开始加入购物车，检查登录状态:', {
      isLoggedIn: app.globalData.isLoggedIn,
      token: app.globalData.token ? '有token' : '无token',
      goodsId: goods.id,
      selectedSpecs: selectedSpecs
    });

    if (!app.globalData.isLoggedIn) {
      wx.showToast({
        title: '请先登录',
        icon: 'none',
        duration: 1500
      });

      setTimeout(() => {
        wx.navigateTo({
          url: '/pages/user/login/login?redirect=/pages/mall/index/index'
        });
      }, 500);
      return;
    }

    wx.showLoading({
      title: '加入中...',
    });

    const that = this;

    wx.request({
      url: api.cart,
      method: 'POST',
      header: {
        'Authorization': 'Bearer ' + app.globalData.token,
        'Content-Type': 'application/json'
      },
      data: {
        product_id: goods.id,
        selected_specs: selectedSpecs,
        quantity: 1
      },
      success: function (res) {
        wx.hideLoading();

        console.log('加入购物车API响应:', {
          statusCode: res.statusCode,
          data: res.data,
          success: res.statusCode === 201 || res.statusCode === 200
        });

        if (res.statusCode === 201 || res.statusCode === 200) {
          wx.showToast({
            title: '加入购物车成功',
            icon: 'success',
            duration: 1500
          });

          // 更新购物车数量
          that.updateCartBadge();

          // 延迟关闭弹窗，让用户看到成功提示
          setTimeout(() => {
            that.closeAddCartPopup();
          }, 1500);
        } else {
          let errorMsg = '加入购物车失败';
          if (res.data && res.data.message) {
            errorMsg = res.data.message;
          } else if (res.data && res.data.detail) {
            errorMsg = res.data.detail;
          }

          wx.showToast({
            title: errorMsg,
            icon: 'none',
            duration: 2000
          });
        }
      },
      fail: function (err) {
        wx.hideLoading();
        console.error('加入购物车网络错误:', err);
        wx.showToast({
          title: '网络错误，请检查网络连接',
          icon: 'none',
          duration: 1500
        });
      }
    });
  },



  // 切换分类时更新名称和商品
  switchCategory(e) {
    const categoryId = e.currentTarget.dataset.id;
    const category = this.data.categories.find(cat => cat.id === categoryId);
    if (category) {
      // 重置分页状态
      this.setData({
        activeCategoryId: categoryId,
        activeCategoryName: category.name,
        'pagination.page': 1,
        'pagination.hasMore': true,
        'pagination.isLoading': false
      });

      // 如果该分类的商品数据还没有加载，则加载
      if (!this.data.categoryGoods[categoryId] || this.data.categoryGoods[categoryId].length === 0) {
        this.getCategoryGoods(categoryId, 1);
      } else {
        // 如果已经有数据，确保显示正确的数据
        this.setData({
          currentCategoryGoods: this.data.categoryGoods[categoryId] || []
        });
      }
    }
  },

  // 输入框事件
  onInput(e) {
    const value = e.detail.value;
    this.setData({
      inputValue: value
    });

    // 如果输入框为空，自动退出搜索状态
    if (!value.trim() && this.data.isSearching) {
      this.cancelSearch();
    }
  },

  // 清除输入
  clearInput() {
    this.setData({
      inputValue: '',
      isSearching: false,
      searchKeyword: '',
      searchResults: []
    });

    // 如果正在搜索，取消搜索
    if (this.data.isSearching) {
      this.cancelSearch();
    }
  },

  /**
   * 搜索事件处理
   */
  onSearch(e) {
    const keyword = e.detail.value || this.data.inputValue.trim();

    if (!keyword) {
      wx.showToast({
        title: '请输入搜索关键词',
        icon: 'none'
      });
      return;
    }

    // 隐藏键盘
    wx.hideKeyboard();

    this.setData({
      isSearching: true,
      searchKeyword: keyword,
      inputValue: keyword, // 保持输入框的值
      'searchPagination.page': 1,
      'searchPagination.hasMore': true,
      searchResults: []
    });

    // 显示加载状态
    wx.showLoading({
      title: '搜索中...',
    });

    // 执行搜索
    this.performSearch(keyword, 1);
  },

  /**
   * 执行搜索请求
   */
  performSearch(keyword, page = 1) {
    if (this.data.searchPagination.isLoading) return;

    this.setData({
      'searchPagination.isLoading': true,
      'searchPagination.page': page
    });

    const that = this;
    const requestUrl = `${api.products}?search=${encodeURIComponent(keyword)}&page=${page}&page_size=${this.data.searchPagination.pageSize}`;

    wx.request({
      url: requestUrl,
      method: 'GET',
      success(res) {
        wx.hideLoading();

        if (res.statusCode === 200) {
          const searchData = res.data;

          // 映射数据格式
          const newSearchResults = searchData.results.map(item => {
            let type = "";
            if (item.is_hot) {
              type = "热销";
            } else if (item.is_new) {
              type = "新品";
            } else if (item.discount_percent > 0) {
              type = "特惠";
            }

            return {
              id: item.id,
              imgUrl: item.main_image || item.image,
              type: type,
              title: item.name,
              currency: "price-icon-point",
              price: item.final_price || item.price,
              originalPrice: item.original_points,
              pointsPrice: item.points_price,
              discountPercent: item.discount_percent,
              isOnSale: item.is_on_sale,
              stock: item.stock,
              salesCount: item.sales_count || 0,
              categoryName: item.category_name,
              rating: item.rating || 0,
              reviewCount: item.review_count || 0
            };
          });

          // 更新搜索结果
          if (page === 1) {
            that.setData({
              searchResults: newSearchResults
            });
          } else {
            that.setData({
              searchResults: [...that.data.searchResults, ...newSearchResults]
            });
          }

          // 更新分页状态
          const hasMore = searchData.next !== null;
          that.setData({
            'searchPagination.hasMore': hasMore,
            'searchPagination.isLoading': false
          });

          // 搜索结果为空提示
          if (page === 1 && newSearchResults.length === 0) {
            wx.showToast({
              title: '未找到相关商品',
              icon: 'none',
              duration: 1500
            });
          }
        } else {
          console.error('搜索商品失败', res);
          that.setData({
            'searchPagination.isLoading': false
          });
          wx.showToast({
            title: '搜索失败，请重试',
            icon: 'none'
          });
        }
      },
      fail(err) {
        wx.hideLoading();
        console.error('搜索接口请求失败', err);
        that.setData({
          'searchPagination.isLoading': false
        });
        wx.showToast({
          title: '网络错误，请重试',
          icon: 'none'
        });
      }
    });
  },

  /**
   * 加载更多搜索结果
   */
  loadMoreSearchResults() {
    if (this.data.searchPagination.hasMore &&
      !this.data.searchPagination.isLoading &&
      this.data.isSearching) {
      const nextPage = this.data.searchPagination.page + 1;
      console.log('加载更多搜索结果，页码:', nextPage);
      this.performSearch(this.data.searchKeyword, nextPage);
    }
  },

  /**
   * 取消搜索，返回页面
   */
  cancelSearch() {
    this.setData({
      isSearching: false,
      searchKeyword: '',
      inputValue: '',
      searchResults: [],
      'searchPagination.page': 1,
      'searchPagination.hasMore': true,
      'searchPagination.isLoading': false
    });
  },


  // 商品详情页跳转路径  
  goToGoodDetail(e) {
    const goodId = e.currentTarget.dataset.id;
    wx.navigateTo({
      url: `/pages/mall/goodsdetail/goodsdetail?id=${goodId}`
    });
  },

  // 切换到分类页面
  goToCategoryPage(e) {
    const categoryId = e.currentTarget.dataset.id;

    // 检查该分类是否存在
    const category = this.data.categories.find(cat => cat.id === categoryId);
    if (!category) {
      wx.showToast({
        title: '分类不存在',
        icon: 'none'
      });
      return;
    }

    // 重置分页状态
    this.setData({
      isCategoryPage: true,
      activeCategoryId: categoryId,
      activeCategoryName: category.name,
      currentCategoryGoods: [], // 清空当前商品列表
      'pagination.page': 1,
      'pagination.hasMore': true,
      'pagination.isLoading': false
    });

    // 获取该分类的商品数据
    this.getCategoryGoods(categoryId, 1);
  },

  /**
   * 获取分类商品数据
   */
  getCategoryGoods(categoryId, page = 1) {

    // 防止重复请求
    if (this.data.pagination.isLoading) {
      return;
    }

    this.setData({
      'pagination.isLoading': true,
      'pagination.page': page
    });

    const that = this;
    const requestUrl = `${api.products}?category=${categoryId}&page=${page}&page_size=5`;

    wx.request({
      url: requestUrl,
      method: 'GET',
      success(res) {

        if (res.statusCode === 200) {
          const categoryGoodsData = res.data;

          // 检查返回数据格式
          if (!categoryGoodsData.results) {
            console.error('返回数据格式错误，缺少results字段', categoryGoodsData);
            that.setData({
              'pagination.isLoading': false
            });
            wx.showToast({
              title: '数据格式错误',
              icon: 'none'
            });
            return;
          }

          // 映射数据格式
          const newGoodsList = categoryGoodsData.results.map(item => {

            // 根据商品属性确定类型标签
            let type = "";
            if (item.is_hot) {
              type = "热销";
            } else if (item.is_new) {
              type = "新品";
            } else if (item.discount_percent > 0) {
              type = "特惠";
            }

            return {
              id: item.id,
              imgUrl: item.main_image || item.image,
              type: type,
              title: item.name,
              currency: "$",
              price: item.final_price || item.price,
              originalPrice: item.original_price,
              pointsPrice: item.points_price,
              discountPercent: item.discount_percent,
              isOnSale: item.is_on_sale,
              stock: item.stock,
              salesCount: item.sales_count || 0,
              categoryName: item.category_name,
              rating: item.rating || 0,
              reviewCount: item.review_count || 0
            };
          });


          // 将数据存储到 categoryGoods[categoryId] 中
          const categoryGoodsKey = `categoryGoods[${categoryId}]`;

          // 判断是否是第一页
          if (page === 1) {
            that.setData({
              [categoryGoodsKey]: newGoodsList,
              currentCategoryGoods: newGoodsList // 同时保留这个用于其他逻辑
            });
          } else {
            // 追加数据
            const existingGoods = that.data.categoryGoods[categoryId] || [];
            that.setData({
              [categoryGoodsKey]: [...existingGoods, ...newGoodsList],
              currentCategoryGoods: [...existingGoods, ...newGoodsList]
            });
          }

          // 更新分页状态 
          const hasMore = categoryGoodsData.next !== null;
          that.setData({
            'pagination.hasMore': hasMore,
            'pagination.isLoading': false
          });

          // 如果没有更多数据，显示提示
          if (!hasMore && page > 1) {
            wx.showToast({
              title: '没有更多商品了',
              icon: 'none',
              duration: 1500
            });
          }

          // 如果第一页就没有数据
          if (page === 1 && newGoodsList.length === 0) {
            wx.showToast({
              title: '该分类下暂无商品',
              icon: 'none',
              duration: 1500
            });
          }
        } else {
          console.error('获取分类商品数据失败', res);
          that.setData({
            'pagination.isLoading': false
          });
          wx.showToast({
            title: '分类商品加载失败',
            icon: 'none'
          });
        }
      },
      fail(err) {
        console.error('分类商品接口请求失败', err);
        that.setData({
          'pagination.isLoading': false
        });
        wx.showToast({
          title: '网络错误，请重试',
          icon: 'none'
        });
      }
    });
  },

  /**
   * 分类页加载更多商品
   */
  loadMoreCategoryGoods() {
    console.log('分类页加载更多，当前状态:', {
      hasMore: this.data.pagination.hasMore,
      isLoading: this.data.pagination.isLoading,
      isCategoryPage: this.data.isCategoryPage,
      currentPage: this.data.pagination.page
    });

    if (this.data.pagination.hasMore &&
      !this.data.pagination.isLoading &&
      this.data.isCategoryPage) {
      const nextPage = this.data.pagination.page + 1;
      console.log('开始加载分类页第', nextPage, '页数据');
      this.getCategoryGoods(this.data.activeCategoryId, nextPage);
    } else {
      console.log('不满足加载更多条件:', {
        hasMore: this.data.pagination.hasMore,
        isLoading: this.data.pagination.isLoading,
        isCategoryPage: this.data.isCategoryPage
      });
    }
  },

  // 返回商城首页
  backToHome() {
    this.setData({
      isCategoryPage: false,
      inputValue: ''
    });
  },

  /**
   * 更新购物车悬浮窗数量徽章
   */
  updateCartBadge() {
    if (!app.globalData.isLoggedIn) {
      this.setData({
        cartBadgeCount: 0
      });
      return;
    }

    const that = this;

    wx.request({
      url: api.cartStats, // 使用正确的 cartStats API
      method: 'GET',
      header: {
        'Authorization': 'Bearer ' + app.globalData.token
      },
      success: function (res) {
        if (res.statusCode === 200) {
          const totalCount = res.data.data?.total_quantity || 0;
          that.setData({
            cartBadgeCount: totalCount
          });
        } else {
          console.error('获取购物车数量失败，状态码:', res.statusCode);
          // 失败时使用本地存储的数量
          const localCart = wx.getStorageSync('cartData') || [];
          const localCount = localCart.reduce((total, item) => total + (item.quantity || 1), 0);
          that.setData({
            cartBadgeCount: localCount
          });
        }
      },
      fail: function (err) {
        console.error('获取购物车数量失败', err);
        // 失败时使用本地存储的数量
        const localCart = wx.getStorageSync('cartData') || [];
        const localCount = localCart.reduce((total, item) => total + (item.quantity || 1), 0);
        that.setData({
          cartBadgeCount: localCount
        });
      }
    });
  },

  /**
   * 点击购物车悬浮窗，跳转到购物车页面
   */
  goToCart() {
    if (!app.globalData.isLoggedIn) {
      wx.showToast({
        title: '请先登录',
        icon: 'none',
        duration: 1500
      });

      setTimeout(() => {
        wx.navigateTo({
          url: '/pages/user/login/login?redirect=/pages/mall/cart/cart'
        });
      }, 500);
      return;
    }

    wx.navigateTo({
      url: '/pages/mall/cart/cart'
    });
  },
  /**
   * 页面上拉触底事件的处理函数
   */
  onReachBottom() {
    if (this.data.isSearching) {
      // 搜索页加载更多
      this.loadMoreSearchResults();
    } else if (this.data.isCategoryPage) {
      // 分类页加载更多
      this.loadMoreCategoryGoods();
    } else {
      // 首页加载更多热门商品
      this.loadMoreGoods();
    }
  },



  /**
   * 页面相关事件处理函数--监听用户下拉动作
   */
  onPullDownRefresh() {
    // 下拉刷新，重新加载第一页数据
    if (!this.data.isCategoryPage) {
      this.getHotGoodsData(1);
    }
    // 停止下拉刷新
    wx.stopPullDownRefresh();
  },

  /**
   * 生命周期函数--监听页面初次渲染完成
   */
  onReady() {},

  /**
   * 生命周期函数--监听页面隐藏
   */
  onHide() {},

  /**
   * 生命周期函数--监听页面卸载
   */
  onUnload() {},

  /**
   * 用户点击右上角分享
   */
  onShareAppMessage() {}
})