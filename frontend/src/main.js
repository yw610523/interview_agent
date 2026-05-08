import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'
import App from './App.vue'
import router from './router'
import draggable from './directives/draggable'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(Antd)

// 注册自定义指令
app.directive('draggable', draggable)

// 确俚Ant Design Vue正确注册
console.log('Ant Design Vue version:', Antd.version)

app.mount('#app')
