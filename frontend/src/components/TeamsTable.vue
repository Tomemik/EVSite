<template>
  <v-container>
    <v-data-table
      :headers="headers"
      :items="teams"
      item-key="name"
      hide-default-footer
      class="teams-table elevation-1"
      :items-per-page="-1"
      sort
    >
      <template v-slot:item="{ item }">
        <tr :style="{ backgroundColor: item.color, color: 'white', textAlign: 'center' }" class="team-row">

          <td>
            <router-link
              :to="{ name: 'team', params: { TName: item.name } }"
              style="color: black; text-decoration: none; font-weight: bold; font-size: 1.1em;"
            >
              {{ item.name }}
            </router-link>
          </td>

          <td style="color: black; font-weight: bold;">
              {{ item.balance.toLocaleString() }}
          </td>

          <td style="color: black; font-weight: 500;">
             {{ item.alliance_name || '-' }}
          </td>

          <td style="color: black; font-weight: bold;">
            <div v-if="item.bounty_value" class="d-flex align-center justify-center">
              <span>{{ item.bounty_value.toLocaleString() }}</span>
            </div>
            <span v-else>-</span>
          </td>

        </tr>
      </template>
    </v-data-table>

    <div v-if="!teams.length && loading" class="d-flex justify-center ma-5">
       <v-progress-circular indeterminate color="primary"></v-progress-circular>
    </div>
  </v-container>
</template>

<script>
export default {
  data() {
    return {
      loading: false,
      headers: [
        { title: 'Team', value: 'name', align: 'center', sortable: true },
        { title: 'Balance', value: 'balance', align: 'center', sortable: true },
        { title: 'Alliance', value: 'alliance_name', align: 'center', sortable: true },
        { title: 'Active Bounty', value: 'bounty_value', align: 'center', sortable: true },
      ],
      teams: [],
    };
  },
  created() {
    this.fetchTeams();
  },
  methods: {
    async fetchTeams() {
      this.loading = true;
      try {
        const response = await fetch('/api/league/teams/');
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        const data = await response.json();
        this.teams = data;
      } catch (error) {
        console.error('Error fetching teams:', error);
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>

<style scoped>
.teams-table .v-data-table__wrapper {
  border: 2px solid #ddd;
}

.team-row {
  border-bottom: 2px solid #fff;
}

.team-row td {
  padding: 12px 16px;
  border-right: 2px solid rgba(0,0,0,0.1);
}

.team-row td:last-child {
  border-right: none;
}
</style>