import { createApp } from 'vue'
import { createPinia } from "pinia";
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'

// Vuetify
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { VCalendar } from 'vuetify/labs/VCalendar'
import '@mdi/font/css/materialdesignicons.css';


// Components
import App from './App.vue'
import VueCookies from "vue-cookies";
import router from './router'
import VueDatePicker from '@vuepic/vue-datepicker';
import '@vuepic/vue-datepicker/dist/main.css'

const app = createApp(App);
const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)
const vuetify = createVuetify({
  defaults: {
    VSelect: {
      density: "compact",
    },
    VDataTable: {
      density: "compact",
    }
  },
  components: {
    ...components,
    VCalendar,
  },
  locale: {
    locale: 'en',
  },
  directives,
  icons: {
    defaultSet: 'mdi',
  },
  theme: {
    defaultTheme: 'dark'
  }
})

app.use(vuetify)
app.use(router)
app.use(VueCookies, { expires: "1d" })
app.use(pinia)
app.component('VueDatePicker', VueDatePicker);
app.mount('#app')
