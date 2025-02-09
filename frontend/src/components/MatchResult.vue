<template>
  <v-dialog v-model="localShowResultsDialog" @update:model-value="close" max-width="800px">
    <v-card>
      <v-card-title>Match Results</v-card-title>
      <v-card-text v-if="detailedMatch">
        <v-select
          v-model="judgeName"
          :items="allTeamNames"
          clearable
          label="Judge"
        ></v-select>

        <v-select
          v-model="winningSide"
          :items="sides"
          label="Winning Side"
          required
        ></v-select>

        <v-text-field
          v-model="roundScore"
          label="Round Score (X:Y | Winning side 1st)"
          :rules="[roundScoreFormat]"
          required
        ></v-text-field>

        <v-divider></v-divider>

        <v-row>
          <v-col>
            <div v-for="(team, teamIndex) in detailedMatch.sides.team_1" :key="team.team">
              <v-row align="center" style="height: 44px;">
                <v-checkbox
                  v-model="teamResults['team_1'][teamIndex].was_present"
                  class="ma-0"
                ></v-checkbox>
                <strong style="height: 44px;">{{ team.team }}:</strong>
              </v-row>

              <v-row>
                <v-text-field
                  v-model="teamResults['team_1'][teamIndex].bonuses"
                  label="Bonuses"
                  type="number"
                  min="0"
                  class="ml-2"
                  style="width: 100px;"
                ></v-text-field>
                <v-text-field
                  v-model="teamResults['team_1'][teamIndex].penalties"
                  label="Penalties"
                  type="number"
                  min="0"
                  class="ml-2"
                  style="width: 100px;"
                ></v-text-field>
              </v-row>

              <!-- Tanks Lost -->
              <ul style="list-style-type: none; padding-left: 0;">
                <li v-for="(tank, tankIndex) in team.tanks" :key="tank.id">
                  <v-row align="center">
                    <v-checkbox
                      v-model="tanksLost['team_1'][teamIndex][tankIndex].used"
                      class="mr-2"
                    ></v-checkbox>

                    <v-text-field
                      v-model="tanksLost['team_1'][teamIndex][tankIndex].quantity"
                      :label="tank.tank.name"
                      type="number"
                      min="0"
                      class="ml-2"
                      style="width: 100px; max-width: 100px;"
                    ></v-text-field>
                  </v-row>
                </li>
              </ul>

              <!-- Add Substitute Button -->
              <v-btn @click="addSubstitute('team_1', teamIndex)" color="primary">Add Substitute</v-btn>
              <div v-for="(substitute, subIndex) in substitutes['team_1'][teamIndex]" :key="subIndex">
                <v-row>
                  <v-select
                    v-model="substitute.team"
                    :items="allTeamNames"
                    label="Substitute Team"
                  ></v-select>
                  <v-text-field
                    v-model="substitute.activity"
                    label="Activity"
                    type="number"
                    min="0"
                    class="ml-2"
                    style="width: 100px;"
                  ></v-text-field>
                  <v-btn @click="removeSubstitute('team_1', teamIndex, subIndex)" color="red">Remove</v-btn>
                </v-row>
              </div>
            </div>
          </v-col>

          <v-col class="d-flex justify-center align-center">
            <p style="text-align:center; font-weight: bold;">vs</p>
          </v-col>

          <v-col class="d-flex flex-column align-end">
            <div v-for="(team, teamIndex) in detailedMatch.sides.team_2" :key="team.team">
              <v-row align="center" style="height: 44px;">
                <v-checkbox
                  v-model="teamResults['team_2'][teamIndex].was_present"
                  class="ma-0"
                ></v-checkbox>
                <strong style="height: 44px;">{{ team.team }}:</strong>
              </v-row>

              <v-row>
                <v-text-field
                  v-model="teamResults['team_2'][teamIndex].bonuses"
                  label="Bonuses"
                  type="number"
                  min="0"
                  class="ml-2"
                  style="width: 100px;"
                ></v-text-field>
                <v-text-field
                  v-model="teamResults['team_2'][teamIndex].penalties"
                  label="Penalties"
                  type="number"
                  min="0"
                  class="ml-2"
                  style="width: 100px;"
                ></v-text-field>
              </v-row>

              <!-- Tanks Lost -->
              <ul style="list-style-type: none; padding-left: 0;">
                <li v-for="(tank, tankIndex) in team.tanks" :key="tank.id">
                  <v-row align="center">
                    <v-checkbox
                      v-model="tanksLost['team_2'][teamIndex][tankIndex].used"
                      class="mr-2"
                    ></v-checkbox>

                    <v-text-field
                      v-model="tanksLost['team_2'][teamIndex][tankIndex].quantity"
                      :label="tank.tank.name"
                      type="number"
                      min="0"
                      class="ml-2"
                      style="width: 100px; max-width: 100px;"
                    ></v-text-field>
                  </v-row>
                </li>
              </ul>

              <!-- Add Substitute Button -->
              <v-btn @click="addSubstitute('team_2', teamIndex)" color="primary">Add Substitute</v-btn>
              <div v-for="(substitute, subIndex) in substitutes['team_2'][teamIndex]" :key="subIndex">
                <v-row>
                  <v-select
                    v-model="substitute.team"
                    :items="allTeamNames"
                    label="Substitute Team"
                  ></v-select>
                  <v-text-field
                    v-model="substitute.activity"
                    label="Activity"
                    type="number"
                    min="0"
                    class="ml-2"
                    style="width: 100px;"
                  ></v-text-field>
                  <v-btn @click="removeSubstitute('team_2', teamIndex, subIndex)" color="red">Remove</v-btn>
                </v-row>
              </div>
            </div>
          </v-col>
        </v-row>
      </v-card-text>

      <v-card-actions>
        <v-btn color="info" @click="copyResults">Copy Results</v-btn>
        <v-btn v-if="userStore.groups.some(i => ['commander', 'judge', 'admin'].includes(i.name))" :disabled="calcOverride" color="success" @click="calcMatch">Calc</v-btn>
        <v-btn v-if="userStore.groups.some(i => ['commander', 'judge', 'admin'].includes(i.name))" :disabled="!canSubmitResults" color="success" @click="submitResults">Submit</v-btn>
        <v-btn
          v-if="userStore.groups.some(i => ['commander', 'judge', 'admin'].includes(i.name))"
          :disabled="!calcOverride"
          color="warning"
          @click="revertCalc"
        >
    Revert Calc
  </v-btn>
        <v-btn color="error" @click="close">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch, computed } from 'vue';
import {useUserStore} from "../config/store.ts";
import {getAuthToken} from "../config/api/user.ts";

const userStore = useUserStore()
const props = defineProps(['detailedMatch', 'showResultsDialog', 'allTeamDetails', 'results', 'calcOverride']);
const emit = defineEmits(['update:showResultsDialog', 'postResults', 'calcMatch', 'revertCalc']);

const localShowResultsDialog = ref(props.showResultsDialog);
const allTeamNames = ref([]);
const calcOverride = ref()

watch(() => props.showResultsDialog, (newValue) => {
  localShowResultsDialog.value = newValue;
});

watch(() => props.calcOverride, (newValue) => {
  calcOverride.value = newValue;
  console.log('calcOverride updated:', newValue);
});

const updateShowResultsDialog = (value) => {
  emit('update:showResultsDialog', value);
};

const close = () => {
  updateShowResultsDialog(false);
};

const sides = ['team_1', 'team_2'];

watch(() => props.allTeamDetails, (newValue) => {
  if (newValue) {
    allTeamNames.value = newValue.map(t => t.name);
  }
});


const judgeName = ref('');
const winningSide = ref('');
const teamResults = ref({});
const tanksLost = ref({});
const substitutes = ref({});
const resultData = ref()
const roundScore = ref('');

const roundScoreFormat = (value) => {
  const regex = /^\d+:\d+$/;
  if (!value) {
    return true;
  }
  return regex.test(value) || 'Invalid score format. Use x:y';
};

const canSubmitResults = computed(() => {
  const roundScoreRegex = /^\d+:\d+$/;
  return winningSide.value && roundScoreRegex.test(roundScore.value);
});

const revertCalc = async () => {
  try {
    await emit('revertCalc', props.detailedMatch.id);
  } catch (error) {
    console.error('Error reverting calculation:', error);
  }
};

watch(() => props.detailedMatch, (newMatch) => {
  if (newMatch) {
    const sides = ['team_1', 'team_2'];
    sides.forEach((side) => {
      teamResults.value[side] = newMatch.sides[side].map(() => ({ bonuses: 0, penalties: 0, was_present: true}));
      tanksLost.value[side] = newMatch.sides[side].map((team) =>
        team.tanks.map((tank) => ({ quantity: 0, used: true, name:tank.tank.name }))
      );
      substitutes.value[side] = newMatch.sides[side].map(() => []);
    });
  }
});


watch(() => props.results, (newResults) => {
  console.log(newResults)
  if (newResults) {
    const sides = ['team_1', 'team_2'];
    sides.forEach((side) => {
      teamResults.value[side] = props.detailedMatch.sides[side].map((team) => {
        const existingResult = newResults?.team_results?.find(
          (result) => result.team === team.team
        ) || {};
        return {
          bonuses: existingResult.bonuses || 0,
          penalties: existingResult.penalties || 0,
          was_present: existingResult.was_present,
        };
      });
      tanksLost.value[side] = props.detailedMatch.sides[side].map((team) => {
        return team.tanks.map((tank) => {
          const lostTankData = newResults?.tanks_lost?.find(
            (lostTank) => lostTank.team === team.team && lostTank.tank === tank.tank.name
          );
          const index = newResults?.tanks_lost?.findIndex(
            (lostTank) => lostTank.team === team.team && lostTank.tank === tank.tank.name
          );

          newResults.tanks_lost[index] = {}

          if (lostTankData) {
            return {
              quantity: lostTankData.quantity,
              used: true,
              name: tank.tank.name,
            }
          } else {
            return {
              quantity: 0,
              used: false,
              name: tank.tank.name
            };
          }
        }).flat();
      });
      substitutes.value[side] = props.detailedMatch.sides[side].map((team) => {
        return (
          newResults?.substitutes?.filter(
            (sub) => sub.team_played_for === team.team
          ) || []
        );
      });
    });
  }

  console.log(teamResults)
  winningSide.value = props.results?.winning_side || '';
  judgeName.value = props.results?.judge || '';
  roundScore.value = props.results?.round_score || '';

});

const addSubstitute = (side, teamIndex) => {
  substitutes.value[side][teamIndex].push({
    team: '',
    team_played_for: { name: props.detailedMatch.sides[side][teamIndex].team },
    activity: 0,
    side: side,
  });
};


const removeSubstitute = (side, teamIndex, subIndex) => {
  if (substitutes.value[side][teamIndex].length > 0) {
    substitutes.value[side][teamIndex].splice(subIndex, 1);
  }
};

const submitResults = () => {
  resultData.value = {
    match_id: props.detailedMatch.id,
    winning_side: winningSide.value,
    judge_name: judgeName.value || '',
    round_score: roundScore.value,
    team_results: Object.keys(teamResults.value).flatMap((side) =>
      teamResults.value[side].map((result, index) => ({
        team_name: props.detailedMatch.sides[side][index].team,
        bonuses: result.bonuses,
        penalties: result.penalties,
        was_present: result.was_present,
      }))
    ),
    tanks_lost: Object.keys(tanksLost.value).flatMap((side) =>
      tanksLost.value[side].flatMap((teamTanks, teamIndex) =>
        teamTanks.filter(tank => tank.used === true).map((tank) => ({
          team_name: props.detailedMatch.sides[side][teamIndex].team,
          tank_name: tank.name,
          quantity: tank.quantity,
          used: tank.used,
        }))
      )
    ),
    substitutes: Object.keys(substitutes.value).flatMap((side) =>
      substitutes.value[side].flatMap((substituteList, teamIndex) =>
        substituteList.map(substitute => ({
          team_name: substitute.team,
          team_played_for_name: substitute.team_played_for.name || substitute.team_played_for,
          team: { name: substitute.team },
          team_played_for: { name: substitute.team_played_for.name || substitute.team_played_for },
          side: substitute.side,
          activity: substitute.activity,
        }))
      )
    ),
  };

  emit('postResults', resultData.value);
};

const prepResults = () => {
    resultData.value = {
    match_id: props.detailedMatch.id,
    winning_side: winningSide.value,
    judge_name: judgeName.value || '',
    round_score: roundScore.value,
    team_results: Object.keys(teamResults.value).flatMap((side) =>
      teamResults.value[side].map((result, index) => ({
        team_name: props.detailedMatch.sides[side][index].team,
        bonuses: result.bonuses,
        penalties: result.penalties,
        side: props.detailedMatch.sides[side][index].side,
        was_present: result.was_present,
      }))
    ),
    tanks_lost: Object.keys(tanksLost.value).flatMap((side) =>
      tanksLost.value[side].flatMap((teamTanks, teamIndex) =>
        teamTanks.filter(tank => tank.used === true).map((tank) => ({
          team_name: props.detailedMatch.sides[side][teamIndex].team,
          tank_name: tank.name,
          quantity: tank.quantity,
          used: tank.used,
        }))
      )
    ),
    substitutes: Object.keys(substitutes.value).flatMap((side) =>
      substitutes.value[side].flatMap((substituteList, teamIndex) =>
        substituteList.map(substitute => ({
          team_name: substitute.team,
          team_played_for_name: substitute.team_played_for.name || substitute.team_played_for,
          team: { name: substitute.team },
          team_played_for: { name: substitute.team_played_for.name || substitute.team_played_for },
          side: substitute.side,
          activity: substitute.activity,
        }))
      )
    ),
  };
}

const gamemodeOptions = [
  { value: 'annihilation', title: 'Annihilation' },
  { value: 'domination', title: 'Domination' },
  { value: 'flag_tank', title: 'Flag Tank' }
];

const bestOfOptions = [
  { value: '3', title: 'Best of 3' },
  { value: '5', title: 'Best of 5' },
];

const modeOptions = [
  { value: 'traditional', title: 'Traditional' },
  { value: 'advanced', title: 'Advanced' },
  { value: 'evolved', title: 'Evolved' }
];

const moneyRulesOptions = [
  { value: 'money_rule', title: 'Money Rule' },
  { value: 'even_split', title: 'Even Split' },
  { value: 'none', title: 'None' }
];

const activityOptions = [
  { value: '1', title: 'Low' },
  { value: '2', title: 'Medium' },
  { value: '3', title: 'High' }
];

const getTitleByValue = (options, value) => {
  const option = options.find(opt => opt.value === value);
  return option ? option.title : value;
};


const copyResults = () => {
  prepResults()
  const match = resultData.value;

  const formatTeamDetails = (teams, tanksLost, substitutes, side) => {
    return teams
      .filter(team => team.side === side)
      .map((team) => {
        const teamTanksLost = tanksLost
          .filter(tank => tank.used === true)
          .filter(tank => tank.team_name === team.team_name)
          .map(tank => `x${tank.quantity} - ${tank.tank_name}`)
          .join('\n');

        const teamSubstitutes = substitutes
          .filter(sub => sub.team_played_for.name === team.team_name)
          .map(sub => `- ${sub.team.name} (${getTitleByValue(activityOptions, String(sub.activity))})`)
          .join('\n');

        const attendanceNote = team.was_present ? '' : '**(No Show)**';

        return `
**${team.team_name}** ${attendanceNote}
Bonuses: ${team.bonuses}
Penalties: ${team.penalties}
Substitutes:
${teamSubstitutes || 'None'}

Tanks Lost:
${teamTanksLost || 'None'}
        `;
      })
      .join('\n');
  };

  const winningSideTeams = match.team_results
    .filter(team => props.detailedMatch.sides[winningSide.value].some(sideTeam => sideTeam.team === team.team_name))
    .map(team => team.team_name)
    .join(' + ');

  const matchResults = `
${formatDateTimeForCopy(props.detailedMatch.datetime)}
${getTitleByValue(gamemodeOptions, props.detailedMatch.gamemode)}, ${getTitleByValue(modeOptions, props.detailedMatch.mode)}, Bo${props.detailedMatch.best_of_number}, ${props.detailedMatch.map_selection}
${getTitleByValue(moneyRulesOptions, props.detailedMatch.money_rules)}
${props.detailedMatch.special_rules || 'None'}

Judge: ${judgeName.value || 'N/A'}

**${winningSideTeams} win ${roundScore.value}**

${formatTeamDetails(match.team_results, match.tanks_lost, match.substitutes, 'team_1')}

--- vs. ---

${formatTeamDetails(match.team_results, match.tanks_lost, match.substitutes, 'team_2')}
  `;

  navigator.clipboard.writeText(matchResults.trim()).then(() => {
    alert('Match results copied to clipboard!');
  }).catch(err => {
    console.error('Failed to copy match results:', err);
  });
};

const calculateBonuses = () => {
  return teamResults.value.team_1.reduce((sum, team) => sum + team.bonuses, 0) +
         teamResults.value.team_2.reduce((sum, team) => sum + team.bonuses, 0);
};

const calculatePenalties = () => {
  return teamResults.value.team_1.reduce((sum, team) => sum + team.penalties, 0) +
         teamResults.value.team_2.reduce((sum, team) => sum + team.penalties, 0);
};

const formatSubstitutes = (substitutes) => {
  if (!substitutes || substitutes.length === 0) return 'None';
  return substitutes
    .map(sub => `${sub.team_name} (${sub.activity})`)
    .join(', ');
};

const formatDateTimeForCopy = (datetime) => {
  const date = new Date(datetime);

  const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  const dayName = days[date.getUTCDay()];

  const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const monthName = months[date.getUTCMonth()];

  const day = date.getUTCDate();
  const ordinal = (n) => {
    const s = ['th', 'st', 'nd', 'rd'];
    const v = n % 100;
    return s[(v - 20) % 10] || s[v] || s[0];
  };
  const dayWithOrdinal = `${day}${ordinal(day)}`;

  const year = date.getUTCFullYear();

  const hours = String(date.getUTCHours()).padStart(2, '0');
  const minutes = String(date.getUTCMinutes()).padStart(2, '0');

  return `${dayName}, ${monthName} ${dayWithOrdinal}, ${year} - ${hours}:${minutes} UTC`;
};

const calcMatch = async () => {
  try {
    await emit('calcMatch', props.detailedMatch.id);
  } catch (error) {
    console.error('Error calculating match:', error);
  }
};

</script>

<style scoped>
.v-select {
  margin-bottom: 10px;
}
</style>