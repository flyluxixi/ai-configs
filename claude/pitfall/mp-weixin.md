# uni-app / 微信小程序（mp-weixin）踩坑记录

## 2026-06-16 - mp-weixin/uni-app 输入负数：type=number 无负号键 + 中文键盘输出全角减号

**现象**: uni-app 编到 mp-weixin，表单需输入负数（如地下楼层 -2）。用 `type="number"` / `type="digit"` 的数字键盘**没有负号键**，根本输不进负数；改用 `type="text"` 后，中文输入法符号区敲出的"减号"往往是**全角 －(U+FF0D)** 或数学减号 −(U+2212)、各类 dash（– — ‐），不是 ASCII 半角 -(U+002D)。清洗函数若只 `replace(/\D/g,'')` 或只 `startsWith('-')` 判断，负号被丢、值变正数；`Number("－2")` 得 NaN，提交/校验出错。
**根因**: ① mp-weixin `<input type="number"/"digit">` 数字键盘不提供负号键（平台设计如此）；② 中文输入法符号面板默认输出全角减号 U+FF0D（及 U+2212 等），与 ASCII 半角 U+002D 是不同 Unicode 码点，正则 `\D` / `startsWith('-')` / `Number()` 都不认。
**解决**: ① 需输负数的字段用 `type="text"`（全键盘才有负号），不用 number/digit；② 清洗函数先归一化各种减号为半角，再保留可选前导负号 + 数字：`const normalized = v.replace(/[－−–—‐]/g, '-'); const neg = normalized.trimStart().startsWith('-'); return (neg ? '-' : '') + normalized.replace(/\D/g, '')`；③ `Number()` 前确保已归一化，避免 NaN。
**标签**: mp-weixin, uni-app, input, type-number, type-text, 负数, 负号, 全角减号, u+ff0d, 半角, 中文输入法, NaN, 清洗归一化

## 2026-06-16 - uni.scss 写实际 CSS 规则被注入每个组件 wxss：tag 选择器触发微信 warn + 包体积膨胀

**现象**: 微信开发者工具满屏 warn（非 error）：`For developer: Some selectors are not allowed in component wxss, including tag name selectors, ID selectors, and attribute selectors.(.../uview-plus/components/u-icon/u-icon.wxss:1:xxxx)`——路径指向 uview-plus 等第三方组件，看似是库的问题，但每个组件都报。
**根因**: 报错的组件 wxss 里其实混入了项目的**全局 reset 样式**（`page/view/text/image/input/button/scroll-view` 等 tag 选择器 + `:root` 变量）。根源是 `src/uni.scss` 里写了**实际 CSS 规则**——uni.scss 是 uni-app 的全局样式注入文件，编译时其全部内容会**注入每个组件和页面的 wxss**。于是含 tag 选择器的规则进了每个组件 wxss，而微信小程序自定义组件 wxss **禁止 tag/ID/属性选择器**（组件样式隔离），每个组件都报这条 warn。warn 级别不报错、功能正常（微信忽略组件内 tag 选择器，同规则在页面级仍生效），但全局 reset 被**重复注入每个组件/页面 wxss → 包体积膨胀**。常见诱因：从原生小程序 `app.wxss` 迁移到 uni-app 时，把全局样式整段搬进了 uni.scss（搬错位置）。
**解决**: uni.scss **只放 scss 变量（`$var`）和 `@mixin`**，不放任何实际 CSS 规则（选择器）。全局基础样式（reset / `:root` CSS 变量 / 字体 / 通用 class）放 **`App.vue` 的非 scoped `<style>`**——它编译成全局 `app.wxss`，允许 tag 选择器、只打包一份。回归风险点：原先 `box-sizing` 等被注入进每个组件内部，迁回 app.wxss 后**不再穿透自定义组件**（app.wxss 全局样式只作用页面、不进组件内部），需验证第三方组件（如 uview-plus）布局无依赖外部 reset 而错位（CSS 自定义变量 `--x` 仍会继承穿透，不受影响）。
**标签**: uni-app, uni.scss, mp-weixin, 微信小程序, 全局样式, app.wxss, 组件样式隔离, tag选择器, component-wxss, 包体积, App.vue, box-sizing

## 2026-06-16 - CSS margin collapse：父无 padding/border 时首个子元素 margin-top 穿透到父外，撑高页面出现意外滚动条

**现象**: 页面内容明显没占满一屏，却出现一根生硬的竖向滚动条、能往下滚一点点。
**根因**: CSS 外边距塌陷（margin collapse）——通用 CSS 机制，但在 mp-weixin 的 `.page`（常设 `min-height: 100vh`）上特别容易踩。父元素若没有 `padding-top` / `border-top` / `overflow` 等，其**第一个子元素的 `margin-top` 会穿透塌陷到父元素外部**，相当于给父加了顶部外边距，使文档总高 = `100vh + 该 margin`，超出视口一点点 → 出现滚动条。尾部子元素的 `margin-bottom` 同理向下穿透。本例：给 `.page` 第一个子元素（搜索框）加 `margin-top: 24rpx`，撑出 24rpx 滚动。
**解决**: 首/尾间距优先用**父元素的 `padding`** 而非子元素的 `margin`（父有 padding 即阻断塌陷）；或给父加 `border-top` / `overflow: hidden` / `display: flex`（flex 容器内子 margin 不塌陷）等任一阻断属性。排查"内容没满却能滚"时先查首/尾子元素有没有纵向 margin 在穿透。
**标签**: css, margin-collapse, 外边距塌陷, 滚动条, 100vh, padding, margin-top, mp-weixin, uni-app, 布局
