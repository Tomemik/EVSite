<template>
  <v-container>
    <v-text-field
      v-model="search"
      label="Search Tanks"
      clearable
      class="mb-6"
    ></v-text-field>

    <v-data-table
      :fixed-header="true"
      :headers="headers"
      :items="tanks"
      item-key="name"
      class="tanks-table elevation-1"
      v-if="tanks.length"
      show-select
      v-model="selected"
      height="calc(100vh - 250px)"
      :items-per-page="15"
      :search="search"
    >
      <template v-slot:[`item.price`]="{ item }">
        <span>{{ item.price.toLocaleString() }}</span>
      </template>
      <template v-slot:bottom>
        <v-row>
          <v-col v-if="userStore.groups.find(i => i.name === 'admin')" cols="auto" class="d-flex align-center">
            <v-btn
              @click="removeTanks"
              color="error"
              :disabled="selected.length === 0"
              class="mx-2"
            >
              Remove Selected Tanks
            </v-btn>
            <v-btn
              @click="openModifyTankDialog"
              color="secondary"
              :disabled="selected.length !== 1"
              class="mr-2"
            >
              Modify Tank
            </v-btn>
            <v-btn
              @click="showAddNewTankDialog=true"
              color="primary"
            >
              Add Tank
            </v-btn>
          </v-col>
          <v-col></v-col>

          <v-col cols="auto" class="d-flex justify-end align-right">
            <v-data-table-footer></v-data-table-footer>
          </v-col>
        </v-row>
      </template>
    </v-data-table>

    <!-- Loading Indicator -->
    <v-progress-circular
      v-else
      indeterminate
      color="primary"
      class="ma-5"
    ></v-progress-circular>

    <!-- Add New Tank Dialog -->
    <v-dialog v-model="showAddNewTankDialog" max-width="500px">
      <v-card>
        <v-card-title>
          <span class="headline">Add New Tank</span>
        </v-card-title>
        <v-card-text>
          <v-form ref="addTankForm">
            <v-text-field
              v-model="newTankName"
              label="Tank Name"
              required
            ></v-text-field>
            <v-text-field
              v-model="newTankBr"
              label="Battle Rating"
              required
            ></v-text-field>
            <v-text-field
              v-model="newTankPrice"
              label="Price"
              required
            ></v-text-field>
            <v-text-field
              v-model="newTankRank"
              label="Rank"
              required
            ></v-text-field>
            <v-text-field
              v-model="newTankType"
              label="Type"
              required
            ></v-text-field>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="addTank">Add Tank</v-btn>
          <v-btn @click="showAddNewTankDialog = false">Cancel</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showModifyTankDialog" max-width="500px">
      <v-card>
        <v-card-title>
          <span class="headline">Tank Details</span>
        </v-card-title>
        <v-card-text>
          <v-form>
            <v-text-field
              v-model="currentTank.name"
              label="Tank Name"
            ></v-text-field>
            <v-text-field
              v-model="currentTank.battle_rating"
              label="Battle Rating"
            ></v-text-field>
            <v-text-field
              v-model="currentTank.price"
              label="Price"
            ></v-text-field>
            <v-text-field
              v-model="currentTank.rank"
              label="Rank"
            ></v-text-field>
            <v-text-field
              v-model="currentTank.type"
              label="Type"
            ></v-text-field>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="modifyTank">Modify</v-btn>
          <v-btn @click="showModifyTankDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script>

import { useUserStore } from "../config/store.ts"
import { getAuthToken } from "../config/api/user.ts"
import { inject, ref } from "vue"

export default {
  data() {
    const userStore = useUserStore();
    const $cookies = inject("$cookies");
    const csrfToken = $cookies.get('csrftoken');

    return {
      headers: [
        { title: 'Name', value: 'name', align: 'center', sortable: true },
        { title: 'Battle Rating', value: 'battle_rating', align: 'center', sortable: true },
        { title: 'Price', value: 'price', align: 'center', sortable: true },
        { title: 'Rank', value: 'rank', align: 'center', sortable: true },
        { title: 'Type', value: 'type', align: 'center', sortable: true },
      ],
      tanks: [],
      selected: [],
      showAddNewTankDialog: false,
      showModifyTankDialog: false,
      newTankName: '',
      newTankBr: '',
      newTankPrice: '',
      newTankRank: '',
      newTankType: '',
      currentTank: '',
      csrfToken,
      userStore,
      search: ref(''),
    };
  },
  created() {
    this.fetchTanks();
  },
  methods: {
    async fetchTanks() {
      try {
        const response = await fetch('/api/league/tanks/');
        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();
        this.tanks = data;
      } catch (error) {
        console.error('Error fetching tanks:', error);
      }
    },
    async addTank() {
      try {
        const response = await fetch(`/api/league/tanks/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': this.csrfToken,
            'Content-Type': 'application/json',
            'Authorization': getAuthToken(),
          },
          body: JSON.stringify({
            name: this.newTankName,
            battle_rating: this.newTankBr,
            price: this.newTankPrice,
            rank: this.newTankRank,
            type: this.newTankType,
          }),
        });

        if (!response.ok) {
          throw new Error('Network response was not ok');
        }

        this.newTankName = '';
        this.newTankBr = '';
        this.newTankPrice = '';
        this.newTankRank = '';
        this.newTankType = '';
        this.showAddNewTankDialog = false;
        this.fetchTanks();
      } catch (error) {
        console.error('There was a problem with the fetch operation:', error);
      }
    },
    async removeTanks() {
      try {
        const response = await fetch(`/api/league/tanks/`, {
          method: 'DELETE',
          headers: {
            'X-CSRFToken': this.csrfToken,
            'Content-Type': 'application/json',
            'Authorization': getAuthToken(),
          },
          body: JSON.stringify({ to_delete: this.selected }),
        });

        if (!response.ok) {
          throw new Error('Network response was not ok');
        }

        this.selected = [];
        await this.fetchTanks();
      } catch (error) {
        console.error('There was a problem with the fetch operation:', error);
      }
    },
    openModifyTankDialog() {
      if (this.selected.length > 0) {
        const selectedTankId = this.selected[0];
        this.currentTank = this.tanks.find(tank => tank.id === selectedTankId);

        if (this.currentTank) {
          this.showModifyTankDialog = true;
        }
      }
    },
    async modifyTank() {
      try {
        const response = await fetch(`/api/league/tanks/` + this.currentTank.name + '/', {
          method: 'PATCH',
          headers: {
            'X-CSRFToken': this.csrfToken,
            'Content-Type': 'application/json',
            'Authorization': getAuthToken(),
          },
          body: JSON.stringify({
            name: this.currentTank.name,
            battle_rating: this.currentTank.battle_rating,
            price: this.currentTank.price,
            rank: this.currentTank.rank,
            type: this.currentTank.type,
          }),
        });

        if (!response.ok) {
          throw new Error('Network response was not ok');
        }

        this.showModifyTankDialog = false;
        await this.fetchTanks();
      } catch (error) {
        console.error('There was a problem with the fetch operation:', error);
      }
    },
  }
};
</script>

<style>
.tanks-table .v-data-table__wrapper {
  border: 1px solid #ddd;
}

.tanks-table .v-data-table__wrapper table tbody tr td {
  margin-left: 24px !important;
}

</style>