// config/settings.js
const baseUrl = 'http://192.168.5.36:8000/recycle/api'

module.exports = {
  baseUrl: baseUrl,

  // 媒体文件
  mediaBaseUrl: 'http://192.168.5.36:8000/media/',

  // 首页轮播图
  banner: baseUrl + '/news/banner/',

  // 新闻
  news: baseUrl + '/news/news/',
  newsCategories: baseUrl + '/news/news_categories/',

  // 商品分类、商品列表、商品创建、商品详情
  mallcategories: baseUrl + '/mall/categories/',
  products: baseUrl + '/mall/products/',
  productCreate: baseUrl + '/mall/products/create/',
  productDetail: baseUrl + '/mall/products/',

  // 商品规格组、商品规格摘要、商品SKU列表、价格计算
  productSpecGroups: baseUrl + '/mall/products/',
  productSpecSummary: baseUrl + '/mall/products/',
  productSkus: baseUrl + '/mall/products/',
  calculatePrice: baseUrl + '/mall/products/calculate_price/',

  // 规格可用性检查、全局规格模板
  checkSpecAvailability: baseUrl + '/mall/products/',
  globalSpecTemplates: baseUrl + '/mall/global_spec_templates/',
  applyGlobalSpec: baseUrl + '/mall/products/',
  recommendednewgoods: baseUrl + '/mall/products/recommended/',
  hotgoods: baseUrl + '/mall/products/hot/',
  newgoods: baseUrl + '/mall/products/new/',

  // 购物车
  cart: baseUrl + '/mall/cart/',
  cartStats: baseUrl + '/mall/cart/stats/',

  // 商城轮播图、价格规则
  banners: baseUrl + '/mall/banners/',
  productPriceRules: baseUrl + '/mall/products/',

  // 用户
  userLogin: baseUrl + '/user/login/',
  userWechatLogin: baseUrl + '/user/wechat_login/',
  userBindPhone: baseUrl + '/user/bind_phone/',
  userProfile: baseUrl + '/user/profile/',
  userLogout: baseUrl + '/user/logout/',
  userRegister: baseUrl + '/user/register/',
  sendSmsCode: baseUrl + '/user/send_sms/',
  phoneLogin: baseUrl + '/user/wechat_phone_login/',
  forgotPassword: baseUrl + '/user/forgot_password/',

  // 员工
  employeeLogin: baseUrl + '/user/employee/login/',
  employeeProfile: baseUrl + '/user/employee/profile/',
  employeeLogout: baseUrl + '/user/employee/logout/',
  employeeApps: baseUrl + '/user/employee/apps/',
  employeeAccessApp: baseUrl + '/user/employee/access_app/',
  adminCreateEmployee: baseUrl + '/admin/create_employee/',

  // JWT Token
  tokenRefresh: baseUrl + '/user/token/refresh/',

  // 地址
  userAddresses: baseUrl + '/user/addresses/',
  userAddressDetail: baseUrl + '/user/addresses/',
  setDefaultAddress: baseUrl + '/user/addresses/',

  // 积分
  pointsRules: baseUrl + '/points/rules/',
  pointsSummary: baseUrl + '/points/summary/',
  pointsSign: baseUrl + '/points/sign/',
  greenLife: baseUrl + '/points/green_life/',
  greenLifeStats: baseUrl + '/points/green_life/stats/',
  pointsRecords: baseUrl + '/points/records/',
  pointsExchange: baseUrl + '/points/exchange/',
  monthlySummary: baseUrl + '/points/monthly_summary/',
  pointsStatus: baseUrl + '/points/status/',
  pointsRanking: baseUrl + '/points/ranking/',
  batchAwardPoints: baseUrl + '/points/admin/batch_award/',

  // 收藏
  userFavorites: baseUrl + '/user/favorites/',
  userFavoriteCreate: baseUrl + '/user/favorites/create/',
  userFavoriteDetail: baseUrl + '/user/favorites/',

  // 优惠券
  userCoupons: baseUrl + '/user/coupons/',
  userCouponDetail: baseUrl + '/user/coupons/',

  // 回收
  scrapCarSubmit: baseUrl + '/recycle/scrap_cars/',
  scrapCarRecords: baseUrl + '/recycle/scrap_cars/',
  scrapCarUpdateStatus: baseUrl + '/recycle/scrap_cars/',

  // 报废车
  scrapCarStats: baseUrl + '/recycle/scrap_cars/stats/',
  scrapCarMyRecords: baseUrl + '/recycle/scrap_cars/my_records/',
  carImageUpload: baseUrl + '/recycle/upload_car_image/',

  // OCR
  recognitionTypes: baseUrl + '/ocr/certificate_types/',
  upload: baseUrl + '/ocr/upload_image/',
  batchUpload: baseUrl + '/ocr/batch_upload/',
  records: baseUrl + '/ocr/recognition_records/',
  myRecords: baseUrl + '/ocr/recognition_records/my_records/',

  // VIN
  vinSearch: baseUrl + '/vin/search/',
  vinQuery: baseUrl + '/vin/query/',
  vinHistory: baseUrl + '/vin/results/',
  vinBatchQuery: baseUrl + '/vin/batch_query/',
  vinStatistics: baseUrl + '/vin/statistics/',
  vinConfigs: baseUrl + '/vin/configs/',

  // API超时设置
  timeout: 10000,

  // 分页设置
  defaultPageSize: 10,
  maxPageSize: 50,

  // 应用配置
  maxImageSize: 20 * 1024 * 1024, // 20MB
  allowedImageTypes: ['image/jpeg', 'image/png', 'image/jpg', 'image/bmp'],
  maxImageCount: 9,
  uploadTimeout: 60000,

  // 图片质量配置
  imageQuality: {
    normal: 0.8,
    high: 0.9,
    low: 0.7
  },
}