import { createRouter, createWebHistory } from 'vue-router';
import Home from '../views/Home.vue';
import Teams from '../views/Teams.vue';
import Team from '../views/Team.vue';
import Tanks from '../views/Tanks.vue';
import Matches from '../views/Matches.vue';
import Manufacturer from "../views/Manufacturer.vue";
import Manufacturers from "../views/Manufacturers.vue";
import Login from '../views/Login.vue';
import Log from "../views/Log.vue";
import Register from "../views/Register.vue";
import Imports from "../views/Imports.vue";

const routes = [
    { path: '/home', name: 'Home', component: Home },
    { path: '/login', name: 'login', component: Login },
    { path: '/teams', name: 'teams', component: Teams },
    { path: '/teams/:TName', name: 'team', component: Team },
    { path: '/teams/:TName/manufacturer', name: 'Manufacturer', component: Manufacturer},
    { path: '/tanks', name: 'tanks', component: Tanks },
    { path: '/matches', name: 'matches', component: Matches },
    { path: '/manufacturers', name: 'manufacturers', component: Manufacturers },
    { path: '/log', name: 'log', component: Log },
    { path: '/register', name: 'register', component: Register },
    { path: '/imports', name: 'imports', component: Imports}
];

const router = createRouter({
    history: createWebHistory(),
    routes,
});
export default router;