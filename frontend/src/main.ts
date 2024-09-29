import { createApp } from 'vue'
import { createPinia } from "pinia";

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

const app = createApp(App);
const pinia = createPinia()
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
})

app.use(vuetify)
app.use(router)
app.use(VueCookies, { expires: "1d" })
app.use(pinia)
app.mount('#app')
