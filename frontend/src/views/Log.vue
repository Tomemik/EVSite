<template>
  <v-container>
    <!-- ============================================================
         FILTERS
    ============================================================= -->
    <v-row>
      <v-col cols="12" md="3">
        <label>Types:</label>

        <v-select
          v-model="selectedMethods"
          :items="methodOptions"
          label="Filter Logs"
          multiple
          clearable
        ></v-select>
      </v-col>

      <v-col cols="12" md="6">
        <label>Date range:</label>

        <VueDatePicker
          v-model="dateFilter"
          range
        />
      </v-col>

      <v-col
        cols="12"
        md="3"
        style="display: flex; align-items: center"
      >
        <v-btn
          color="primary"
          @click="fetchLogs"
        >
          Apply Filters
        </v-btn>
      </v-col>
    </v-row>

    <!-- ============================================================
         LOG GRID
    ============================================================= -->
    <v-row class="logs-table">
      <!-- ==========================================================
           STICKY TEAM / MONEY COLUMNS
      =========================================================== -->
      <v-col
        cols="2"
        class="sticky-container"
      >
        <v-sheet>
          <v-row
            v-for="(Team, TeamIndex) in teams"
            :key="TeamIndex"
            class="align-center sticky-row"
            style="
              padding: 0;
              margin: 0;
              height: 40px;
            "
          >
            <!-- Team name -->
            <v-col
              cols="6"
              class="grid-cell sticky-col"
            >
              <v-sheet
                class="
                  pa-0
                  elevation-1
                  grid-cell-content
                "
                :style="{
                  backgroundColor: Team.color
                }"
                height="100%"
              >
                <div class="Team-name">
                  {{ Team.name }}
                </div>
              </v-sheet>
            </v-col>

            <!-- Team money -->
            <v-col
              cols="6"
              class="grid-cell sticky-col"
            >
              <v-sheet
                class="
                  pa-0
                  elevation-1
                  grid-cell-content
                "
                :style="{
                  backgroundColor: Team.color
                }"
                height="100%"
              >
                <div class="Team-money">
                  {{ Team.balance }}
                </div>
              </v-sheet>
            </v-col>
          </v-row>
        </v-sheet>
      </v-col>

      <!-- ==========================================================
           SCROLLABLE LOGS
      =========================================================== -->
      <v-col
        cols="10"
        class="scrollable-container"
      >
        <v-sheet>
          <v-row
            v-for="(Team, TeamIndex) in teams"
            :key="TeamIndex"
            class="align-center"
            style="
              padding: 0;
              margin: 0;
              height: 40px;
            "
          >
            <v-col
              cols="12"
              class="grid-cell"
            >
              <v-row
                no-gutters
                class="logs-container"
              >
                <v-col
                  v-for="(log, logIndex) in filteredLogsByTeam(Team.name)"
                  :key="logIndex"
                  cols="auto"
                  class="
                    pa-0
                    log-interactive
                    grid-cell-content
                  "
                  :style="{
                    backgroundColor: log.color
                  }"
                  @click="openLogDetails(log)"
                >
                  <div class="log-entry">
                    <div
                      class="log-amount"
                      :class="amountClass(log.amount)"
                    >
                      {{ formatAmount(log.amount) }}
                    </div>

                    <div class="log-desc">
                      {{ log.description }}
                    </div>
                  </div>
                </v-col>
              </v-row>
            </v-col>
          </v-row>
        </v-sheet>
      </v-col>
    </v-row>

    <!-- ============================================================
         LOG DETAILS DIALOG
    ============================================================= -->
    <v-dialog
      v-model="isDialogOpen"
      max-width="600px"
    >
      <v-card>
        <v-card-title>
          Log Details
        </v-card-title>

        <v-card-text>
          <!-- ======================================================
               BASIC DETAILS
          ======================================================= -->
          <div class="mb-4">
            <div>
              <strong>Amount:</strong>

              <span :class="amountClass(selectedLog?.amount)">
                {{ formatAmount(selectedLog?.amount) }}
              </span>
            </div>

            <div>
              <strong>Description:</strong>
              {{ selectedLog?.description }}
            </div>

            <div>
              <strong>Date:</strong>
              {{ selectedLog?.date }}
            </div>

            <div>
              <strong>User:</strong>
              {{ selectedLog?.user }}
            </div>
          </div>

          <!-- ======================================================
               AUCTION PURCHASE
          ======================================================= -->
          <div v-if="selectedLog?.auction">
            <v-divider class="mb-4"></v-divider>

            <div class="text-h6 mb-3">
              Auction Purchase
            </div>

            <v-table
              density="compact"
              class="mb-4 elevation-1"
            >
              <tbody>
                <tr>
                  <td>
                    <strong>Tank</strong>
                  </td>

                  <td
                    class="
                      text-right
                      font-weight-bold
                    "
                  >
                    {{ selectedLog.auction.tank }}
                  </td>
                </tr>

                <tr>
                  <td>
                    <strong>Winning Bid</strong>
                  </td>

                  <td
                    class="
                      text-right
                      text-error
                      font-weight-bold
                    "
                  >
                    -{{
                      selectedLog.auction.winningBid
                        .toLocaleString()
                    }}
                  </td>
                </tr>

                <tr>
                  <td>
                    <strong>Auction Lot</strong>
                  </td>

                  <td class="text-right">
                    #{{ selectedLog.auction.lotId }}
                  </td>
                </tr>
              </tbody>
            </v-table>

          </div>

          <!-- ======================================================
               ECONOMIC BREAKDOWN
          ======================================================= -->
          <div v-else-if="selectedLog?.breakdown">
            <v-divider class="mb-4"></v-divider>

            <div class="text-h6 mb-2">
              Economy Breakdown
            </div>

            <v-table
              density="compact"
              class="mb-4 elevation-1"
            >
              <tbody>
                <tr>
                  <td>
                    <strong>Base Reward</strong>
                  </td>

                  <td class="text-right">
                    {{
                      selectedLog.breakdown
                        .base_reward
                        ?.toLocaleString()
                      || 0
                    }}
                  </td>
                </tr>

                <tr
                  v-if="
                    selectedLog.breakdown
                      .kill_rewards > 0
                  "
                >
                  <td>
                    <strong>Kill Rewards</strong>
                  </td>

                  <td
                    class="
                      text-right
                      text-success
                    "
                  >
                    +{{
                      selectedLog.breakdown
                        .kill_rewards
                        .toLocaleString()
                    }}
                  </td>
                </tr>

                <tr
                  v-if="
                    selectedLog.breakdown
                      .repair_costs > 0
                  "
                >
                  <td>
                    <strong>Repair Costs</strong>
                  </td>

                  <td
                    class="
                      text-right
                      text-error
                    "
                  >
                    -{{
                      selectedLog.breakdown
                        .repair_costs
                        .toLocaleString()
                    }}
                  </td>
                </tr>

                <tr
                  v-if="
                    selectedLog.breakdown
                      .bonuses > 0
                  "
                >
                  <td>
                    <strong>Bonuses</strong>
                  </td>

                  <td
                    class="
                      text-right
                      text-success
                    "
                  >
                    +{{
                      selectedLog.breakdown
                        .bonuses
                        .toLocaleString()
                    }}
                  </td>
                </tr>

                <tr
                  v-if="
                    selectedLog.breakdown
                      .penalties > 0
                  "
                >
                  <td>
                    <strong>Penalties</strong>
                  </td>

                  <td
                    class="
                      text-right
                      text-error
                    "
                  >
                    -{{
                      selectedLog.breakdown
                        .penalties
                        .toLocaleString()
                    }}
                  </td>
                </tr>

                <tr
                  v-if="
                    selectedLog.breakdown
                      .booster_multiplier !== 1
                  "
                >
                  <td>
                    <strong>
                      Booster Multiplier
                    </strong>
                  </td>

                  <td
                    class="
                      text-right
                      text-primary
                    "
                  >
                    x{{
                      selectedLog.breakdown
                        .booster_multiplier
                    }}
                  </td>
                </tr>

                <tr
                  v-if="
                    selectedLog.breakdown
                      .substitute_cut > 0
                  "
                >
                  <td>
                    <strong>
                      Substitutes Cut
                    </strong>
                  </td>

                  <td
                    class="
                      text-right
                      text-error
                    "
                  >
                    -{{
                      selectedLog.breakdown
                        .substitute_cut
                        .toLocaleString()
                    }}
                  </td>
                </tr>

                <tr
                  v-if="
                    selectedLog.breakdown
                      .substitute_earnings > 0
                  "
                >
                  <td>
                    <strong>Sub Earnings</strong>
                  </td>

                  <td
                    class="
                      text-right
                      text-success
                    "
                  >
                    +{{
                      selectedLog.breakdown
                        .substitute_earnings
                        .toLocaleString()
                    }}
                  </td>
                </tr>

                <tr
                  v-if="
                    selectedLog.breakdown
                      .judge_reward > 0
                  "
                >
                  <td>
                    <strong>Judge Reward</strong>
                  </td>

                  <td
                    class="
                      text-right
                      text-success
                    "
                  >
                    +{{
                      selectedLog.breakdown
                        .judge_reward
                        .toLocaleString()
                    }}
                  </td>
                </tr>

                <tr
                  v-if="
                    selectedLog.breakdown
                      .bounty_reward > 0
                  "
                >
                  <td>
                    <strong>Bounty Reward</strong>
                  </td>

                  <td
                    class="
                      text-right
                      text-success
                    "
                  >
                    +{{
                      selectedLog.breakdown
                        .bounty_reward
                        .toLocaleString()
                    }}
                  </td>
                </tr>

                <tr
                  v-if="
                    selectedLog.breakdown
                      .soft_cap_multiplier !== 1
                  "
                >
                  <td>
                    <strong>
                      Soft Cap Penalty
                    </strong>
                  </td>

                  <td
                    class="
                      text-right
                      text-error
                    "
                  >
                    x{{
                      selectedLog.breakdown
                        .soft_cap_multiplier
                        .toFixed(2)
                    }}
                  </td>
                </tr>

                <tr
                  class="final-total-row"
                >
                  <td>
                    <strong>Final Total</strong>
                  </td>

                  <td
                    class="
                      text-right
                      font-weight-bold
                    "
                  >
                    {{
                      selectedLog.breakdown
                        .final_reward
                        ?.toLocaleString()
                      || 0
                    }}
                  </td>
                </tr>
              </tbody>
            </v-table>

            <!-- ====================================================
                 KILL / REPAIR DETAILS
            ===================================================== -->
            <v-row>
              <v-col
                cols="6"
                v-if="
                  selectedLog.breakdown
                    .kill_details?.length
                "
              >
                <div
                  class="
                    text-subtitle-2
                    mb-1
                    text-center
                    font-weight-bold
                  "
                >
                  Kill Details
                </div>

                <v-table
                  density="compact"
                  class="elevation-1"
                >
                  <thead>
                    <tr>
                      <th>Tank</th>

                      <th class="text-center">
                        Qty
                      </th>

                      <th class="text-right">
                        Reward
                      </th>
                    </tr>
                  </thead>

                  <tbody>
                    <tr
                      v-for="
                        (kill, idx)
                        in selectedLog.breakdown
                          .kill_details
                      "
                      :key="idx"
                    >
                      <td class="text-caption">
                        {{ kill.tank }}
                      </td>

                      <td
                        class="
                          text-center
                          text-caption
                        "
                      >
                        {{ kill.qty }}
                      </td>

                      <td
                        class="
                          text-right
                          text-success
                          text-caption
                        "
                      >
                        +{{
                          kill.reward
                            .toLocaleString()
                        }}
                      </td>
                    </tr>
                  </tbody>
                </v-table>
              </v-col>

              <v-col
                cols="6"
                v-if="
                  selectedLog.breakdown
                    .repair_details?.length
                "
              >
                <div
                  class="
                    text-subtitle-2
                    mb-1
                    text-center
                    font-weight-bold
                  "
                >
                  Repair Details
                </div>

                <v-table
                  density="compact"
                  class="elevation-1"
                >
                  <thead>
                    <tr>
                      <th>Tank</th>

                      <th class="text-center">
                        Qty
                      </th>

                      <th class="text-right">
                        Cost
                      </th>
                    </tr>
                  </thead>

                  <tbody>
                    <tr
                      v-for="
                        (repair, idx)
                        in selectedLog.breakdown
                          .repair_details
                      "
                      :key="idx"
                    >
                      <td class="text-caption">
                        {{ repair.tank }}
                      </td>

                      <td
                        class="
                          text-center
                          text-caption
                        "
                      >
                        {{ repair.qty }}
                      </td>

                      <td
                        class="
                          text-right
                          text-error
                          text-caption
                        "
                      >
                        -{{
                          repair.cost
                            .toLocaleString()
                        }}
                      </td>
                    </tr>
                  </tbody>
                </v-table>
              </v-col>
            </v-row>
          </div>

          <!-- ======================================================
               GENERIC LOG
          ======================================================= -->
          <div v-else>
            <v-divider class="mb-4"></v-divider>

            <div>
              <strong>Details:</strong>

              <span
                v-html="
                  selectedLog?.full_details
                "
              ></span>
            </div>
          </div>
        </v-card-text>

        <v-card-actions>
          <v-spacer></v-spacer>

          <v-btn
            color="primary"
            @click="closeLogDetails"
          >
            Close
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import {
  onMounted,
  ref,
} from 'vue';


/* ================================================================
   TYPES
================================================================ */

interface Team {
  name: string;
  balance: string;
  color: string;
}


interface AuctionLogData {
  lotId: number;
  tank: string;
  winningBid: number;
}


interface Log {
  team: string;
  user: string;

  amount: string;

  description: string;
  full_details: string;

  color: string;
  date: string;

  breakdown?: any;

  auction?: AuctionLogData | null;
}


/* ================================================================
   STATE
================================================================ */

const teams =
  ref<Team[]>([]);

const logs =
  ref<Log[]>([]);

const selectedMethods =
  ref<any[]>([]);

const dateFilter =
  ref<
    [Date | null, Date | null]
    | null
  >(null);


const isDialogOpen =
  ref(false);

const selectedLog =
  ref<Log | null>(null);


/* ================================================================
   FILTER OPTIONS
================================================================ */

const methodOptions = [
  {
    title: 'Match Reward',
    value: 'calc_rewards'
  },

  {
    title: 'Sub Reward',
    value: 'sub_rewards'
  },

  {
    title: 'Judge Reward',
    value: 'judge_rewards'
  },

  {
    title: 'Judge + Sub',
    value: 'judge_and_sub_rewards'
  },

  {
    title: 'Match Reverted',
    value: 'revert_rewards'
  },

  {
    title: 'Tank Bought',
    value: 'purchase_tank'
  },

  {
    title: 'Tank Sold',
    value: 'sell_tank'
  },

  {
    title: 'Tank Sold',
    value: 'sell_teamtank'
  },

  {
    title: 'Tank Upgraded',
    value: 'upgrade_or_downgrade_tank'
  },

  {
    title: 'Money Transfers In',
    value: 'money_transfer_in'
  },

  {
    title: 'Money Transfers Out',
    value: 'money_transfer_out'
  },

  {
    title: 'Imports Purchase',
    value: 'imports_purchase'
  },

  {
    title: 'Auction Won',
    value: 'auction_win'
  },

  {
    title: 'Box Opened',
    value: 'open_tank_box'
  },

  {
    title: 'Box Purchased',
    value: 'purchase_box'
  },

  {
    title: 'Weekly Payout',
    value: 'weekly_under_cap_bonus'
  },
];


/* ================================================================
   DISPLAY HELPERS
================================================================ */

function filteredLogsByTeam(
  teamName: string
) {
  return logs.value
    .filter(
      log =>
        log.team === teamName
    )
    .sort(
      (a, b) =>
        new Date(b.date).getTime()
        - new Date(a.date).getTime()
    );
}


function formatAmount(
  value?: string | null
): string {
  if (
    value === undefined
    || value === null
    || value === ''
  ) {
    return '0';
  }

  const amount =
    Number(value);

  if (!Number.isFinite(amount)) {
    return value;
  }

  return amount
    .toLocaleString();
}


function amountClass(
  value?: string | null
) {
  const amount =
    Number(value ?? 0);

  if (amount > 0) {
    return 'positive-amount';
  }

  if (amount < 0) {
    return 'negative-amount';
  }

  return '';
}


/* ================================================================
   DIALOG
================================================================ */

function openLogDetails(
  log: Log
) {
  selectedLog.value =
    log;

  isDialogOpen.value =
    true;
}


function closeLogDetails() {
  isDialogOpen.value =
    false;

  selectedLog.value =
    null;
}


/* ================================================================
   TEAMS
================================================================ */

const fetchTeams =
  async () => {
    try {
      const response =
        await fetch(
          '/api/league/teams/'
        );

      if (!response.ok) {
        throw new Error(
          'Network response was not ok'
        );
      }

      const data =
        await response.json();

      teams.value =
        data.sort(
          (a: Team, b: Team) =>
            a.name.localeCompare(
              b.name
            )
        );

    } catch (error) {
      console.error(
        'Error fetching teams:',
        error
      );
    }
  };


/* ================================================================
   AUCTION LOG PARSING
================================================================ */

/*
 * Current backend auction_win description:
 *
 *     Won Auction Lot #12: Black Prince for 171600.
 *
 * We parse that directly, so this works with the auction
 * backend you already have deployed.
 */
function parseAuctionWin(
  log: any
): AuctionLogData | null {
  if (
    log.method_name
    !== 'auction_win'
  ) {
    return null;
  }

  const description =
    String(
      log.description ?? ''
    );


  const match =
    description.match(
      /Won Auction Lot #(\d+):\s*(.*?)\s+for\s+([0-9]+(?:\.[0-9]+)?)\.?\s*$/i
    );


  if (match) {
    return {
      lotId:
        Number(match[1]),

      tank:
        match[2].trim(),

      winningBid:
        Number(match[3]),
    };
  }


  /*
   * Fallback in case the text format is changed slightly.
   */
  const bidMatch =
    description.match(
      /for\s+([0-9]+(?:\.[0-9]+)?)/i
    );


  return {
    lotId: 0,

    tank:
      description
        .replace(
          /^Won Auction Lot #[0-9]+:\s*/i,
          ''
        )
        .replace(
          /\s+for\s+[0-9]+(?:\.[0-9]+)?\.?\s*$/i,
          ''
        )
        .trim()
      || 'Auction Tank',

    winningBid:
      bidMatch
        ? Number(bidMatch[1])
        : 0,
  };
}


/* ================================================================
   LOG FETCH
================================================================ */

const fetchLogs =
  async () => {
    try {
      const now =
        new Date();

      const startOfMonth =
        new Date(
          now.getFullYear(),
          now.getMonth(),
          1
        );

      const endOfMonth =
        new Date(
          now.getFullYear(),
          now.getMonth() + 1,
          0,
          23,
          59,
          59
        );


      if (
        !dateFilter.value
        || !dateFilter.value.length
      ) {
        dateFilter.value = [
          startOfMonth,
          endOfMonth,
        ];
      }


      const params =
        new URLSearchParams();


      if (
        selectedMethods.value.length
        > 0
      ) {
        selectedMethods.value
          .forEach(
            method => {
              params.append(
                'method_name',
                method
              );
            }
          );
      }


      if (
        dateFilter.value
        && dateFilter.value[0]
        && dateFilter.value[1]
      ) {
        params.append(
          'from_date',
          dateFilter.value[0]
            .toISOString()
        );

        params.append(
          'to_date',
          dateFilter.value[1]
            .toISOString()
        );
      }


      const response =
        await fetch(
          `/api/league/transactions/money_log/?${params.toString()}`
        );


      if (!response.ok) {
        throw new Error(
          'Network response was not ok'
        );
      }


      const data =
        await response.json();


      /* ==========================================================
         COLORS
      =========================================================== */

      const colorMapping:
        Record<string, string> = {

        'calc_rewards':
          '#9fc5e8',

        'sub_rewards':
          '#ffe599',

        'judge_rewards':
          '#3c78d8',

        'judge_and_sub_rewards':
          '#3c78d8',

        'revert_rewards':
          '#808080',

        'purchase_tank':
          '#dd7e6b',

        'sell_tank':
          '#cc4125',

        'sell_teamtank':
          '#cc4125',

        'upgrade_or_downgrade_tank':
          '#a64d79',

        'do_direct_upgrade':
          '#a64d79',

        'money_transfer_in':
          '#38761d',

        'money_transfer_out':
          '#38761d',

        'imports_purchase':
          '#cccccc',

        /*
         * Auction purchase:
         * purple so it is clearly distinct from
         * normal tank purchases/imports.
         */
        'auction_win':
          '#8e7cc3',

        'open_tank_box':
          '#46bdc6',

        'purchase_box':
          '#46bdc6',

        'weekly_under_cap_bonus':
          '#4e98ec',
      };


      /* ==========================================================
         LABELS
      =========================================================== */

      const descMapping:
        Record<string, string> = {

        'calc_rewards':
          'Match Reward',

        'sub_rewards':
          'Sub Reward',

        'judge_rewards':
          'Judge Reward',

        'judge_and_sub_rewards':
          'Judge + Sub',

        'revert_rewards':
          'Match Reverted',

        'purchase_tank':
          'Tank Bought',

        'sell_tank':
          'Tank Sold',

        'sell_teamtank':
          'Tank Sold',

        'upgrade_or_downgrade_tank':
          'Tank Upgraded',

        'do_direct_upgrade':
          'Tank Upgraded',

        'money_transfer_in':
          'Transfer In',

        'money_transfer_out':
          'Transfer Out',

        'imports_purchase':
          'Imports',

        'auction_win':
          'Auction Won',

        'open_tank_box':
          'Box Opened',

        'purchase_box':
          'Box Purchased',

        'weekly_under_cap_bonus':
          'Weekly Payout',
      };


      /*
       * Defensive filter:
       *
       * Even if the backend endpoint has not yet been restarted
       * with the exclusion below, bid escrow/refund logs will
       * never be rendered by this page.
       */
      const visibleResults =
        data.results.filter(
          (log: any) =>
            ![
              'auction_bid_hold',
              'auction_outbid_refund',
            ].includes(
              log.method_name
            )
        );


      logs.value =
        visibleResults.map(
          (log: any) => {
            /* ====================================================
               GENERIC BALANCE AMOUNT
            ===================================================== */

            const amountMatch =
              String(
                log.description ?? ''
              ).match(
                /Balance Changed by:\s*([+-]?\d+(?:\.\d+)?)/
              );


            let amount =
              amountMatch
                ? String(
                    Math.round(
                      Number(
                        amountMatch[1]
                      )
                    )
                  )
                : '0';


            let desc =
              descMapping[
                log.method_name
              ]
              || log.method_name
              || 'Log';


            let auction:
              AuctionLogData | null =
                null;


            /* ====================================================
               AUCTION WIN
            ===================================================== */

            if (
              log.method_name
              === 'auction_win'
            ) {
              auction =
                parseAuctionWin(log);


              if (auction) {
                /*
                 * The actual balance was escrowed during bidding,
                 * but economically this transaction is the purchase
                 * of the tank for the winning bid.
                 */
                amount =
                  String(
                    -auction.winningBid
                  );


                /*
                 * Show the useful information directly in
                 * the horizontal grid.
                 */
                desc =
                  auction.tank;
              }
            }


            /* ====================================================
               TANK BOUGHT
            ===================================================== */

            else if (
              desc === 'Tank Bought'
            ) {
              const addedMatch =
                String(
                  log.description ?? ''
                ).match(
                  /Added Tanks:\s*(.*)/
                );


              desc =
                addedMatch
                  ? addedMatch[1]
                      .replace(
                        /\*\*/g,
                        ''
                      )
                      .trim()
                  : 'N/A';
            }


            /* ====================================================
               TANK SOLD
            ===================================================== */

            else if (
              desc === 'Tank Sold'
            ) {
              const removedMatch =
                String(
                  log.description ?? ''
                ).match(
                  /Removed Tanks:\s*(.*)/
                );


              desc =
                removedMatch
                  ? removedMatch[1]
                      .replace(
                        /\*\*/g,
                        ''
                      )
                      .trim()
                  : 'N/A';
            }


            /* ====================================================
               TANK UPGRADED
            ===================================================== */

            else if (
              desc === 'Tank Upgraded'
            ) {
              const addedMatch =
                String(
                  log.description ?? ''
                ).match(
                  /Added Tanks:\s*(.*)/
                );


              const addedTanks =
                addedMatch
                  ? addedMatch[1]
                      .replace(
                        /\*\*/g,
                        ''
                      )
                      .trim()
                  : 'N/A';


              const removedMatch =
                String(
                  log.description ?? ''
                ).match(
                  /Removed Tanks:\s*(.*)/
                );


              const removedTanks =
                removedMatch
                  ? removedMatch[1]
                      .replace(
                        /\*\*/g,
                        ''
                      )
                      .trim()
                  : 'N/A';


              desc =
                `${removedTanks} -> ${addedTanks}`;
            }


            return {
              team:
                log.team_name,

              user:
                log.user
                || 'system',

              amount,

              /*
               * Note:
               * Your old component calculated `desc` above but
               * accidentally returned descMapping[...] instead.
               *
               * This intentionally returns the processed value.
               */
              description:
                desc,

              full_details:
                String(
                  log.description ?? ''
                ).replace(
                  /\n/g,
                  '<br>'
                ),

              color:
                colorMapping[
                  log.method_name
                ]
                || '#FFFFFF',

              date:
                new Date(
                  log.timestamp
                ).toLocaleString(),

              breakdown:
                log.new_value
                  ?.breakdown
                || null,

              auction,
            } as Log;
          }
        );

    } catch (error) {
      console.error(
        'Error fetching logs:',
        error
      );
    }
  };


/* ================================================================
   LIFECYCLE
================================================================ */

onMounted(() => {
  fetchTeams();
  fetchLogs();
});
</script>

<style scoped>
.logs-table {
  display: flex;
  flex-wrap: nowrap;

  width: 100%;

  overflow-x: hidden;

  padding-left: 10px;
  padding-right: 10px;
}


.sticky-container {
  position: sticky;

  left: 0;

  z-index: 10;

  margin: 0;
  padding: 0;
}


.scrollable-container {
  display: flex;
  flex-wrap: nowrap;

  overflow-x: auto;

  width: 100%;

  padding-top: 15px;
  padding-bottom: 15px;

  margin: 0;
  padding: 0;
}


.grid-cell {
  padding: 0;
  margin: 0;

  box-sizing: border-box;

  height: 100%;

  color: black;
}


.grid-cell-content {
  border: 1px solid black;

  box-sizing: border-box;

  color: black;
}


.Team-name,
.Team-money {
  display: flex;

  justify-content: center;
  align-items: center;

  text-align: center;

  height: 30px;

  font-weight: bold;
  font-size: 1rem;
}


.Team-money {
  font-weight: bold;
}


.sticky-col {
  position: sticky;

  z-index: 10;
}


.sticky-col:nth-child(1) {
  left: 0;

  z-index: 2;

  width: 80px;
}


.sticky-col:nth-child(2) {
  left: 80px;

  z-index: 2;

  width: 80px;
}


.logs-container {
  display: flex;

  flex-wrap: nowrap;

  overflow-x: auto;

  width: 100%;
  height: 100%;

  padding: 0;
  margin: 0;

  overflow: hidden;
}


.log-entry {
  display: flex;

  flex-direction: row;

  justify-content: space-between;
  align-items: center;

  width: 200px;
  height: 100%;

  padding: 1px 4px;
  margin: 0 2px;

  box-sizing: border-box;

  cursor: pointer;
}


.log-amount {
  flex: 1;

  font-weight: bold;
  font-size: 1rem;

  white-space: nowrap;
}


.log-desc {
  flex: 1;

  font-size: 0.8rem;

  margin-left: 0;

  white-space: nowrap;

  overflow: hidden;
  text-overflow: ellipsis;
}

.positive-amount {
  color: #09571b;
}


.negative-amount {
  color: #650a0a;
}


.final-total-row {
  background-color: #3b3b3b;
  color: white;
}
</style>