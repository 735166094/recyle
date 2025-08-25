Page({
  data: {
    // 收藏列表
    favorites: [],
    // 购物车数量
    cartCount: 0
  },

  onShow() {
    // 每次显示页面时加载收藏数据
    this.loadFavoritesData();
    // 获取购物车数量
    this.getCartCount();
  },

  // 加载收藏数据
  loadFavoritesData() {
    // 从本地存储获取收藏数据
    const favorites = wx.getStorageSync('favorites') || [];
    
    this.setData({
      favorites: favorites
    });
  },

  // 从后端获取收藏数据的预留方法
  fetchFavoritesFromBackend() {
    // 实际项目中，应从后端获取当前用户的收藏数据
    wx.request({
      url: 'https://your-backend-url.com/api/favorites',
      method: 'GET',
      header: {
        'Authorization': 'Bearer ' + wx.getStorageSync('token')
      },
      success: (res) => {
        if (res.data.success) {
          this.setData({
            favorites: res.data.data
          });
        }
      },
      fail: (err) => {
        console.error('获取收藏数据失败', err);
      }
    });
  },

  // 取消收藏
  removeFavorite(e) {
    const index = e.currentTarget.dataset.index;
    const { favorites } = this.data;
    
    // 显示确认对话框
    wx.showModal({
      title: '提示',
      content: '确定要取消收藏该商品吗？',
      success: (res) => {
        if (res.confirm) {
          // 用户确认取消收藏
          const removedItem = favorites[index];
          favorites.splice(index, 1);
          
          this.setData({
            favorites: favorites
          });
          
          // 更新本地存储
          wx.setStorageSync('favorites', favorites);
          
          // 同步到后端的预留方法
          this.removeFavoriteFromBackend(removedItem.id);
          
          wx.showToast({
            title: '已取消收藏',
            icon: 'none',
            duration: 1500
          });
        }
      }
    });
  },

  // 从后端取消收藏的预留方法
  removeFavoriteFromBackend(goodsId) {
    wx.request({
      url: `https://your-backend-url.com/api/favorites/${goodsId}`,
      method: 'DELETE',
      header: {
        'Authorization': 'Bearer ' + wx.getStorageSync('token')
      },
      success: (res) => {
        if (!res.data.success) {
          console.error('取消收藏失败', res.data.message);
        }
      },
      fail: (err) => {
        console.error('取消收藏失败', err);
      }
    });
  },

  // 添加到购物车
  addToCart(e) {
    const index = e.currentTarget.dataset.index;
    const favoriteItem = this.data.favorites[index];
    
    // 从收藏列表中获取商品信息
    let goods = {
      id: favoriteItem.id,
      title: favoriteItem.title,
      imgUrl: favoriteItem.imgUrl,
      price: favoriteItem.price,
      currency: favoriteItem.currency
    };
    
    // 从本地存储中获取购物车数据
    let cartData = wx.getStorageSync('cartData') || [];
    const existingItemIndex = cartData.findIndex(item => item.id === goods.id);
    
    if (existingItemIndex > -1) {
      // 如果已存在，数量加1
      cartData[existingItemIndex].quantity += 1;
    } else {
      // 如果不存在，添加到购物车
      cartData.push({
        ...goods,
        quantity: 1
      });
    }
    
    // 保存到本地存储
    wx.setStorageSync('cartData', cartData);
    
    // 显示提示
    wx.showToast({
      title: '已加入购物车',
      icon: 'success',
      duration: 1500
    });
    
    // 更新购物车数量显示
    this.getCartCount();
    
    // 同步到后端的预留方法
    this.syncCartToBackend(cartData);
  },

  // 同步购物车数据到后端的预留方法
  syncCartToBackend(cartData) {
    wx.request({
      url: 'https://your-backend-url.com/api/cart',
      method: 'POST',
      header: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + wx.getStorageSync('token')
      },
      data: {
        items: cartData
      },
      success: (res) => {
        if (!res.data.success) {
          console.error('同步购物车数据失败', res.data.message);
        }
      },
      fail: (err) => {
        console.error('同步购物车数据到后端失败', err);
      }
    });
  },

  // 获取购物车数量
  getCartCount() {
    const cartData = wx.getStorageSync('cartData') || [];
    const count = cartData.reduce((total, item) => total + item.quantity, 0);
    this.setData({
      cartCount: count
    });
  },

  // 跳转到商品详情
  goToGoodDetail(e) {
    const goodsId = e.currentTarget.dataset.id;
    wx.navigateTo({
      url: `/pages/gooddetail/gooddetail?id=${goodsId}`
    });
  },

  // 跳转到购物车
  goToCart() {
    wx.navigateTo({
      url: '/pages/cart/cart'
    });
  },

  // 去购物
  goShopping() {
    wx.navigateBack({
      delta: 1 // 返回上一级页面，通常是商城首页
    });
  }
});
