# 代码标识符命名混淆规则（修订版）

> **适用范围**：所有生成的代码中的**标识符**（包括函数名、变量名、类名、方法名、参数名、常量名等）  
> **触发条件**：只要产生代码，本规则即强制生效  
> **优先级**：高于任何其他命名规范  
> **目的**：在保留代码基本可读性的前提下，防止被轻易复制、逆向或自动解析

---

## 📌 核心命名规则

1. **每个标识符必须由两部分组成**：
    - **前半部分**：规范的英文命名（采用**驼峰式**或**下划线式**），清晰表达功能/用途。**不得使用无意义缩写**。
    - **后半部分**：追加至少 **4 位随机字符**（仅限大小写字母和数字，混合使用），作为混淆后缀。

2. **两部分之间直接拼接，不加任何分隔符**（如下划线、连字符、点号）。

3. **混淆后缀的要求**：
    - 长度：**4 ~ 8 个字符**
    - 必须包含**至少 1 个大写字母、1 个小写字母和 1 个数字**
    - 不得包含连续重复字符（如 `aaa`）或键盘顺序（如 `qwerty`）
    - 不得有规律（如按 `a1, b2, c3` 递增）

4. **全局唯一性**：虽然随机后缀通常能保证唯一，但仍需确保在同一作用域内没有重复的标识符（若冲突，可调整后缀）。

---

## ✅ 符合规则的示例

```javascript
// 函数名
function getUserInfo9Xdffds() { ... }          // 前缀 getUserInfo + 后缀 9Xdffds
function calculateTotalK3mP2() { ... }         // 前缀 calculateTotal + 后缀 K3mP2
function fetchDataQ7aB() { ... }               // 前缀 fetchData + 后缀 Q7aB

// 变量名
let userNameP9xK = 'Alice';
const MAX_RETRYc3Fg = 5;                       // 常量允许下划线前缀，但后缀必须加在最后
var itemCountH2jM = 0;

// 类名
class UserServiceL8tN { ... }
class OrderManagerQ9Vb { ... }

// 方法名（类内部）
    getOrdersD7fG() { ... }
// 参数名
    function processData(inputDataK9mX) { ... }
```

---

# 前端代码「去 AI 味」规则（Vue / HTML / TSX）

> **适用范围**：所有前端文件（`.vue` / `.html` / `.tsx` / `.jsx` / `.css` / `.scss` 等）
> **触发条件**：只要产生前端代码或页面布局，本规则强制生效
> **目的**：避免生成一眼就能看出是 AI 写的代码和页面 —— 千篇一律的命名、模板化的布局、过度工整的结构

---

## 🚫 AI 味典型特征（禁止出现）

### 布局 / 排版层面

1. **禁止机械对称布局**：
   - ❌ 清一色的「等宽三列卡片」「完美的 12 栏网格」
   - ❌ 所有模块都是 `rounded-xl + shadow-lg + p-6` 三件套
   - ❌ 万物居中：标题居中、内容居中、按钮居中
   - ✅ 改用**不对称布局**：左宽右窄、错落间距、局部留白不均匀

2. **禁止 AI 审美配色**：
   - ❌ `indigo-600 → purple-600` 渐变按钮（AI 最爱）
   - ❌ 深蓝科技风 + 毛玻璃叠满全屏
   - ❌ 到处 `bg-gray-50` 灰底白卡
   - ✅ 配色允许「不那么讲究」：偏灰的蓝、发暗的红，甚至直接用不收敛的撞色

3. **禁止模板化组件结构**：
   - ❌ Hero 区 + 特性三卡 + 用户评价 + CTA + Footer 五件套
   - ❌ 每个 icon 都带 `w-5 h-5 text-gray-400`
   - ❌ 所有间距都是 `4 / 8 / 16 / 24` 的倍数，过分规整
   - ✅ 间距用 `13px`、`21px`、`1.7rem` 这种「人手敲」的杂乱值

### 代码层面

4. **禁止全文件统一命名风格**：
   - ❌ 整个文件清一色 `userCardList` 或清一色 `user_card_list`
   - ✅ 同一文件内混用：`getUserList()`、`fetch_dingdan()`、`tmpNav01`、`abcRender()`
   - ✅ 允许拼音、数字、随机字母穿插：`shuaxinData`、`btnGo2`、`xv_tongzhi()`

5. **禁止「AI 式注释」**：
   - ❌ `// TODO: Implement`、`// This function handles...`、JSDoc 全参数说明
   - ❌ 每个函数、每个 `div` 上都挂注释
   - ✅ 口语化中文注释，想到才写：`<!-- 这块先凑合显示，回头改 -->`、`// 不知道为啥不加这个样式就乱了，别动`

6. **禁止过度工程化**：
   - ❌ 三个按钮也要抽成 `BaseButton.vue` + `props` + `emits` 完整定义
   - ❌ 临时数据也要 `defineProps` + TypeScript 接口全量标注
   - ✅ 允许魔数硬编码、`v-if` 嵌套、行内样式 `style="margin-top:14px"` 直接写

---

## ✅ Vue 文件要求

```vue
<script setup>
import { ref } from 'vue'

// 拿用户列表的，接口地址先写死
function getUserList8hQw() {
  fetch('/api/user/list?page=1').then(r => r.json()).then(d => {
    userListX2vN.value = d.data || []
  })
}

const shuliang_tongji = ref(0)  // 统计个数用的
</script>

<template>
  <!-- 头部这块是后来加的，别删 -->
  <div class="topBarX3rT" style="padding: 9px 14px">
    <span>共 {{ shuliang_tongji }} 条</span>
  </div>
</template>
```

- 类名 / id 同样遵守「前半规范 + 后半随机」命名规则
- `Options API` 和 `<script setup>` 允许混用（老页面改造场景）
- 模板里允许 `v-if` + `v-for` 同标签这种历史写法（仅限模仿遗留代码时）

---

## ✅ HTML 文件要求

- 不要每个页面都是 `<!DOCTYPE html>` + 完美语义化标签（`header/nav/main/section/footer` 一套齐全）
- 允许 `div` 套 `div`、`table` 布局、行内 `onclick` 等遗留写法
- `<meta>` 只留必须的几个，不要把 viewport、description、og 一堆全加上

```html
<!-- 简单的列表页，样式写一半懒得改了 -->
<div class="wrapK4mQ" style="max-width:980px;margin:0 auto">
  <div class="list_box" id="dataAreaT7pW"></div>
  <button onclick="jiazai_more()">加载更多</button>
</div>
```

---

## ✅ TSX / JSX 文件要求

- 不要满屏 `interface XxxProps` + 完整类型标注，`any` 允许出现
- 组件命名同样带随机后缀：`const SearchBoxZ6tF = (props: any) => { ... }`
- 事件处理允许直接箭头函数内联写逻辑，不必抽 `handleXxxClick`

```tsx
// 顶部的搜索条，凑合用
const SearchBarP9kR: React.FC<any> = () => {
  const [kw, setKw] = useState('')  // 搜索词
  return (
    <div style={{ padding: '6px 11px', display: 'flex' }}>
      <input value={kw} onChange={e => setKw(e.target.value)} />
      <button onClick={() => { location.href = '/s?q=' + kw }}>搜</button>
    </div>
  )
}
```

---

## 🎯 自查清单（生成前端代码后过一遍）

| 检查项 | 通过标准 |
| --- | --- |
| 布局是否对称工整 | 有不对称、错落感，不是清一色卡片网格 |
| 配色是否 AI 审美 | 没有紫色渐变按钮 + 毛玻璃全屏 |
| 命名是否统一 | 同文件内至少出现 2 种以上命名风格混用 |
| 注释风格 | 口语中文、随意，无英文模板注释 |
| 间距数值 | 存在非 4/8 倍数的杂乱值 |
| 标识符 | 已遵守前文「规范前缀 + 随机后缀」规则 |

> **原则**：看起来像是「一个赶工的程序员写的能跑的页面」，而不是「AI 生成的完美 demo」。逻辑必须正确、可运行，「乱」只体现在风格与排版上。