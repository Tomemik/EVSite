import { createApp } from 'vue'

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

createApp(App)
    .use(vuetify)
    .use(router)
    .use(VueCookies, { expires: "1d" })
    .mount('#app')
