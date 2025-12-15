<template>
  <v-dialog v-model="localShowResultsDialog" @update:model-value="close" max-width="1000px">
    <v-card class="rounded-lg">
      <v-toolbar color="primary" density="compact">
        <v-toolbar-title class="text-subtitle-1 font-weight-bold">
          <v-icon start icon="mdi-clipboard-check"></v-icon>
          Match Results
        </v-toolbar-title>
        <v-spacer></v-spacer>
        <v-btn icon @click="close">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-toolbar>

      <v-card-text class="pa-6">
        <v-form>
          <v-row dense>
            <v-col cols="12" md="4">
              <v-select
                v-model="judgeName"
                :items="allTeamNames"
                clearable
                label="Judge"
                prepend-inner-icon="mdi-gavel"
                variant="outlined"
                density="compact"
              ></v-select>
            </v-col>

            <v-col cols="12" md="4">
              <v-select
                v-model="winningSide"
                :items="sides"
                label="Winning Side"
                required
                prepend-inner-icon="mdi-trophy"
                variant="outlined"
                density="compact"
              ></v-select>
            </v-col>

            <v-col cols="12" md="4">
              <v-text-field
                v-model="roundScore"
                label="Round Score (X:Y)"
                placeholder="Winning side 1st"
                :rules="[roundScoreFormat]"
                required
                prepend-inner-icon="mdi-scoreboard"
                variant="outlined"
                density="compact"
              ></v-text-field>
            </v-col>
          </v-row>

          <v-divider class="my-6"></v-divider>

          <v-row v-if="detailedMatch">
            <v-col cols="12" md="5">
              <div class="text-subtitle-1 mb-2 text-center font-weight-bold text-primary">Team 1</div>

              <div v-for="(team, teamIndex) in detailedMatch.sides.team_1" :key="team.team" class="mb-4">
                <v-card variant="outlined" class="border-grey">
                  <v-card-item class="bg-grey-lighten-1 py-1">
                    <div class="d-flex align-center">
                      <v-checkbox
                        v-model="teamResults['team_1'][teamIndex].was_present"
                        hide-details
                        density="compact"
                        class="mr-2"
                      ></v-checkbox>
                      <span class="text-subtitle-2 font-weight-bold">{{ team.team }}</span>
                    </div>
                  </v-card-item>

                  <v-divider></v-divider>

                  <v-card-text class="pa-3">
                    <v-row dense class="mb-2">
                      <v-col cols="6">
                        <v-text-field
                          v-model="teamResults['team_1'][teamIndex].bonuses"
                          label="Bonuses"
                          type="number"
                          min="0"
                          variant="outlined"
                          density="compact"
                          hide-details
                          prepend-inner-icon="mdi-star"
                        ></v-text-field>
                      </v-col>
                      <v-col cols="6">
                        <v-text-field
                          v-model="teamResults['team_1'][teamIndex].penalties"
                          label="Penalties"
                          type="number"
                          min="0"
                          variant="outlined"
                          density="compact"
                          hide-details
                          prepend-inner-icon="mdi-alert-circle"
                        ></v-text-field>
                      </v-col>
                    </v-row>

                    <v-divider class="my-3 border-dashed"></v-divider>
                    <div class="text-caption font-weight-bold text-medium-emphasis mb-2">TANKS LOST</div>

                    <div
                      v-for="(tank, tankIndex) in team.tanks"
                      :key="tank.id"
                      class="d-flex align-center mb-1"
                    >
                      <v-checkbox-btn
                        v-model="tanksLost['team_1'][teamIndex][tankIndex].used"
                        density="compact"
                        class="mr-2"
                      ></v-checkbox-btn>

                      <div class="text-body-2 text-truncate flex-grow-1" :class="{'text-decoration-line-through text-disabled': !tanksLost['team_1'][teamIndex][tankIndex].used}">
                        {{ tank.tank.name }}
                      </div>

                      <v-text-field
                        v-model="tanksLost['team_1'][teamIndex][tankIndex].quantity"
                        type="number"
                        min="0"
                        variant="outlined"
                        density="compact"
                        hide-details
                        style="max-width: 70px;"
                        :disabled="!tanksLost['team_1'][teamIndex][tankIndex].used"
                      ></v-text-field>
                    </div>

                    <v-divider class="my-3 border-dashed"></v-divider>

                    <div class="d-flex justify-space-between align-center mb-2">
                      <div class="text-caption font-weight-bold text-medium-emphasis">SUBSTITUTES</div>
                      <v-btn
                        size="x-small"
                        variant="tonal"
                        color="primary"
                        prepend-icon="mdi-account-plus"
                        @click="addSubstitute('team_1', teamIndex)"
                      >Add</v-btn>
                    </div>

                    <div v-for="(substitute, subIndex) in substitutes['team_1'][teamIndex]" :key="subIndex" class="pa-2 rounded mb-2 border">
                      <v-select
                        v-model="substitute.team"
                        :items="allTeamNames"
                        label="Sub Team"
                        density="compact"
                        variant="outlined"
                        hide-details
                        class="mb-2"
                      ></v-select>
                      <div class="d-flex align-center">
                        <v-select
                          v-model="substitute.activity"
                          label="Activity"
                          :items="activityOptions"
                          item-title="title"
                          item-value="value"
                          density="compact"
                          variant="outlined"
                          hide-details
                        ></v-select>
                        <v-btn
                          icon="mdi-delete"
                          size="small"
                          variant="text"
                          color="error"
                          class="ml-2"
                          @click="removeSubstitute('team_1', teamIndex, subIndex)"
                        ></v-btn>
                      </div>
                    </div>

                  </v-card-text>
                </v-card>
              </div>
            </v-col>

            <v-col cols="12" md="2" class="d-flex justify-center align-center">
               <div class="text-h5 text-disabled font-italic font-weight-black">VS</div>
            </v-col>

            <v-col cols="12" md="5">
              <div class="text-subtitle-1 mb-2 text-center font-weight-bold text-error">Team 2</div>

              <div v-for="(team, teamIndex) in detailedMatch.sides.team_2" :key="team.team" class="mb-4">
                <v-card variant="outlined" class="border-grey">
                  <v-card-item class="bg-grey-lighten-1 py-1">
                    <div class="d-flex align-center">
                      <v-checkbox
                        v-model="teamResults['team_2'][teamIndex].was_present"
                        hide-details
                        density="compact"
                        class="mr-2"
                      ></v-checkbox>
                      <span class="text-subtitle-2 font-weight-bold">{{ team.team }}</span>
                    </div>
                  </v-card-item>

                  <v-divider></v-divider>

                  <v-card-text class="pa-3">
                    <v-row dense class="mb-2">
                      <v-col cols="6">
                        <v-text-field
                          v-model="teamResults['team_2'][teamIndex].bonuses"
                          label="Bonuses"
                          type="number"
                          min="0"
                          variant="outlined"
                          density="compact"
                          hide-details
                          prepend-inner-icon="mdi-star"
                        ></v-text-field>
                      </v-col>
                      <v-col cols="6">
                        <v-text-field
                          v-model="teamResults['team_2'][teamIndex].penalties"
                          label="Penalties"
                          type="number"
                          min="0"
                          variant="outlined"
                          density="compact"
                          hide-details
                          prepend-inner-icon="mdi-alert-circle"
                        ></v-text-field>
                      </v-col>
                    </v-row>

                    <v-divider class="my-3 border-dashed"></v-divider>
                    <div class="text-caption font-weight-bold text-medium-emphasis mb-2">TANKS LOST</div>

                    <div
                      v-for="(tank, tankIndex) in team.tanks"
                      :key="tank.id"
                      class="d-flex align-center mb-1"
                    >
                      <v-checkbox-btn
                        v-model="tanksLost['team_2'][teamIndex][tankIndex].used"
                        density="compact"
                        class="mr-2"
                      ></v-checkbox-btn>

                      <div class="text-body-2 text-truncate flex-grow-1" :class="{'text-decoration-line-through text-disabled': !tanksLost['team_2'][teamIndex][tankIndex].used}">
                        {{ tank.tank.name }}
                      </div>

                      <v-text-field
                        v-model="tanksLost['team_2'][teamIndex][tankIndex].quantity"
                        type="number"
                        min="0"
                        variant="outlined"
                        density="compact"
                        hide-details
                        style="max-width: 70px;"
                        :disabled="!tanksLost['team_2'][teamIndex][tankIndex].used"
                      ></v-text-field>
                    </div>

                    <v-divider class="my-3 border-dashed"></v-divider>

                    <div class="d-flex justify-space-between align-center mb-2">
                      <div class="text-caption font-weight-bold text-medium-emphasis">SUBSTITUTES</div>
                      <v-btn
                        size="x-small"
                        variant="tonal"
                        color="primary"
                        prepend-icon="mdi-account-plus"
                        @click="addSubstitute('team_2', teamIndex)"
                      >Add</v-btn>
                    </div>

                    <div v-for="(substitute, subIndex) in substitutes['team_2'][teamIndex]" :key="subIndex" class="pa-2 rounded mb-2 border">
                      <v-select
                        v-model="substitute.team"
                        :items="allTeamNames"
                        label="Sub Team"
                        density="compact"
                        variant="outlined"
                        hide-details
                        class="mb-2"
                      ></v-select>
                      <div class="d-flex align-center">
                        <v-select
                          v-model="substitute.activity"
                          label="Activity"
                          type="number"
                          :items="activityOptions"
                          item-title="title"
                          item-value="value"
                          density="compact"
                          variant="outlined"
                          hide-details
                        ></v-select>
                        <v-btn
                          icon="mdi-delete"
                          size="small"
                          variant="text"
                          color="error"
                          class="ml-2"
                          @click="removeSubstitute('team_2', teamIndex, subIndex)"
                        ></v-btn>
                      </div>
                    </div>

                  </v-card-text>
                </v-card>
              </div>
            </v-col>
          </v-row>
        </v-form>
      </v-card-text>

      <v-divider></v-divider>

      <v-card-actions class="pa-4">
        <v-btn
          color="info"
          variant="text"
          prepend-icon="mdi-content-copy"
          @click="copyResults"
        >Copy Results</v-btn>

        <v-spacer></v-spacer>

        <template v-if="userStore.groups.some(i => ['commander', 'judge', 'admin'].includes(i.name))">
          <v-btn
            v-if="calcOverride"
            color="warning"
            variant="tonal"
            prepend-icon="mdi-undo"
            @click="revertCalc"
          >Revert Calc</v-btn>

          <v-btn
            :disabled="calcOverride"
            color="success"
            variant="tonal"
            prepend-icon="mdi-calculator"
            @click="calcMatch"
          >Calc</v-btn>

          <v-btn
            :disabled="!canSubmitResults"
            color="success"
            variant="elevated"
            prepend-icon="mdi-check"
            @click="submitResults"
          >Submit</v-btn>
        </template>

        <v-btn
          color="error"
          variant="text"
          @click="close"
        >Close</v-btn>
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

          if (index !== -1 && newResults.tanks_lost) {
              newResults.tanks_lost[index] = {}
          }

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
    activity: null,
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
.border-grey {
  border-color: #BDBDBD !important;
}
.border-dashed {
  border-style: dashed;
}
</style>