<template>
  <v-container>
    <v-data-table
      :headers="headers"
      :items="teams"
      item-key="name"
      hide-default-footer
      class="teams-table elevation-1"
      v-if="teams.length"
      :items-per-page="25"
    >
      <template v-slot:item="{ item }">
        <tr :style="{ backgroundColor: item.color, color: 'white', textAlign: 'center' }" class="team-row">
          <td>
            <router-link
              :to="{ name: 'team', params: { TName: item.name } }"
              style="color: black; text-decoration: none; font-weight: bold;"
            >
              {{ item.name }}
            </router-link>
          </td>
          <td style="color: black; text-decoration: none; font-weight: bold;">
              {{ item.balance }}
          </td>
        </tr>
      </template>
    </v-data-table>
    <v-progress-circular
      v-else
      indeterminate
      color="primary"
      class="ma-5"
    ></v-progress-circular>
  </v-container>
</template>

<script>
export default {
  data() {
    return {
      headers: [
        { title: 'Teams', value: 'name', align: 'center' },
        { title: 'Balance', value: 'balance', align: 'center' },
      ],
      teams: [],
    };
  },
  created() {
    this.fetchTeams();
  },
  methods: {
    async fetchTeams() {
      try {
        const response = await fetch('/api/league/teams/');
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        const data = await response.json();
        this.teams = data.sort((a, b) => a.name.localeCompare(b.name));
      } catch (error) {
        console.error('Error fetching teams:', error);
      }
    },
  },
};
</script>

<style>
.teams-table .v-data-table__wrapper {
  border: 1px solid #ddd;
}

.team-row {
  border-bottom: 1px solid #ddd;
  text-align: center;
}

.team-row td {
  padding: 16px;
  text-align: center;
  border: 1px solid #000;
  color: black;
}


</style>