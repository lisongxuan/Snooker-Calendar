// Home.vue
<template>
  <el-config-provider namespace="ep">
    <BaseHeader />
    <div class="flex main-container">
      <div class="custom-width py-4">
        <!--
        <div class="flex-row">
          <el-input
            v-model="inputValue"
            size="large"
            :placeholder="$t('app.jumpIntoContent')"
            clearable
            :suffix-icon="Search"
            @input="handleInputChange"
          />
        </div>
        <el-button v-if="contextFlag" @click="handleReturn()" type="primary" style="margin: 10px;">{{$t('app.returnSearch')}}</el-button>
        <el-pagination
          background
          layout="prev, pager, next"
          :total="pagination.total"
          :page-size="pagination.per_page"
          :current-page.sync="pagination.page"
          @current-change="handlePageChange"
          style="margin-top: 10px;"
        />
        -->
        <div class="flex-row">
          <el-tag>{{ $t('app.latestPlayerInfoDate') }}: {{ playerInfoDate ? playerInfoDate: $t('app.noData') }}</el-tag>
          <el-tag>{{ $t('app.latestEventInfoDate') }}: {{  eventInfoDate ? eventInfoDate : $t('app.noData') }}</el-tag>
        </div>
        <el-table :data="tableData"  class="custom-table">
          <el-table-column prop="position" :label="$t('app.position')"  />
          <el-table-column :label="$t('app.name')" >
            <template #default="{ row }">
              <div>{{ row.surname_first ? `${row.lastname} ${row.firstname}` : `${row.firstname} ${row.lastname}` }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="sum_value" :label="$t('app.sumValue')" />
          <el-table-column prop="num_ranking_titles" :label="$t('app.rankingTitles')"  />
          <el-table-column :label="$t('app.downloadICS')" >
            <template #default="{ row }">
              <el-button v-if="row.last_updated" type="primary" size="small" @click="downloadICS(row.player_id)">Download</el-button>
            </template>
          </el-table-column>
          <el-table-column :label="$t('app.googleCalendar')" >
            <template #default="{ row }">
              <el-button v-if="row.last_updated" type="success" size="small" @click="addToGoogleCalendar(row.player_id)">Add to Calendar</el-button>
            </template>
          </el-table-column>
          <el-table-column :label="$t('app.lastUpdated')" >
            <template #default="{ row }">
              <span>{{ row.last_updated || $t('app.noData') }}</span>
            </template>
          </el-table-column>
        </el-table>
        <div class="footer-text">
          <el-divider></el-divider>
          All Data from Snooker.org
        </div>
      </div>
    </div>
  </el-config-provider>
</template>

<script lang="ts" setup>
import { ref, reactive, onMounted, provide, watch } from 'vue'
import axios from 'axios';
import { Search } from '@element-plus/icons-vue'
import config from './config';
import Cookies from 'js-cookie';
import { useI18n } from 'vue-i18n';
const { t ,locale} = useI18n();
onMounted(() => {
  const storedPageLanguage = Cookies.get('pageLanguage');
      if (storedPageLanguage) {
        locale.value = JSON.parse(storedPageLanguage);
      }
  document.title = t('header.title');
});
interface Pagination {
  total: number;
  page: number;
  per_page: number;
}
const playerInfoDate=ref('');
const eventInfoDate=ref('');
const tempPaginationNumber = ref(10);
const paginationNumber =ref(10);
const inputValue = ref('')
const languages: { [key: string]: string } = reactive({
  'en': t('app.en'),
  'jp': t('app.jp'),
  'cn': t('app.cn'),
  'de': t('app.de'),
  'fr': t('app.fr'),
  'kr': t('app.kr')
});

const tableData = ref<RowType[]>([]);
const defaultLanguage = ref(config.defaultLanguage);
const tempDefaultLanguage = ref(config.defaultLanguage);
const pagination = reactive<Pagination>({
  total: 0,
  page: 1,
  per_page: 10
});
var cacheData= ref<RowType[]>([]);
var cachePagination= reactive<Pagination>({
  total: 0,
  page: 1,
  per_page: 10
});
var contextFlag=ref(false);
watch(paginationNumber, (newValue) => {
      Cookies.set('paginationNumber', newValue.toString(), { expires: 7 }); // cookies有效期为7天
    });

    watch(defaultLanguage, (newValue) => {
      Cookies.set('defaultLanguage', JSON.stringify(newValue), { expires: 7 }); // cookies有效期为7天
    });
    watch(locale, () => {
  languages.en = t('app.en');
  languages.jp = t('app.jp');
  languages.cn = t('app.cn');
  languages.de = t('app.de');
  languages.fr = t('app.fr');
  languages.kr = t('app.kr');
});



interface RowType {
  type: number;
  firstname: string;
  lastname: string;
  surname_first: boolean;
  nationality: string;
  born: string;
  num_ranking_titles: number;
  position: number;
  player_id: number;
  sum_value: number;
  last_updated: string;
  [key: string]: any;
}


const handleInputChange = (value: string, newSearchFlag: boolean = true) => {
  if(inputValue.value === '' || inputValue.value === null || inputValue.value === undefined ||contextFlag.value===true) {
    return;
  }
  if (newSearchFlag) {
  pagination.total= 0;
  pagination.page= 1;
  pagination.per_page= 10;}

};
const handlePageChange = (page: number) => {
  pagination.page = page;
  handleInputChange(inputValue.value, false);
};
const handleReturn = () => {
  tableData.value=cacheData.value;
  contextFlag.value=false;
  if (pagination.per_page==cachePagination.per_page){
    pagination.total=cachePagination.total;
    pagination.page=cachePagination.page;
    pagination.per_page=cachePagination.per_page;
  }
  else{
    handleInputChange(inputValue.value, false);
  }

};

const downloadICS = (playerId: number) => {
  const url = `${config.backendUrl}/api/calendar?${playerId}`;
  window.open(url, '_blank');
};

const addToGoogleCalendar = (playerId: number) => {
  const url = `https://www.google.com/calendar/render?cid=${config.backendUrl}/static/${playerId}.ics`;
  window.open(url, '_blank');
};

const getPlayers = async () => {
  const result = await axios.get(`${config.backendUrl}/api/players`);
  return result.data;
};
const getLastUpdated = async () => {
  const result = await axios.get(`${config.backendUrl}/api/info/lastupdated`);
  return result.data;
};

onMounted(async () => {
  try {
       // 加载玩家数据
       const playersData = await getPlayers();
    tableData.value = playersData;
    const dataDate = await getLastUpdated();
    for (const item of dataDate) {
      if (item.info === 'players') {
        playerInfoDate.value = item.lastupdated;
      } else if (item.type === 'events') {
        eventInfoDate.value = item.lastupdated;
      }
    }
const storedPaginationNumber = Cookies.get('paginationNumber');
      if (storedPaginationNumber) {
        paginationNumber.value = parseInt(storedPaginationNumber, 10);
        pagination.per_page = paginationNumber.value;
        tempPaginationNumber.value = paginationNumber.value;
      }
const storedDefaultLanguage = Cookies.get('defaultLanguage');
      if (storedDefaultLanguage) {
        defaultLanguage.value = JSON.parse(storedDefaultLanguage);
        tempDefaultLanguage.value = JSON.parse(storedDefaultLanguage);
      }
  } catch (error) {
    console.error("Failed to fetch data:", error);
  }
});
</script>

<style>
.main-container {
  margin-left: 2%;
}
.custom-width {
  width: 95%;
}
.custom-table {
  margin-bottom: 20px;
}
.el-table .highlight {
  background-color: yellow;
}
.flex-row {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
}
.footer-text {
  margin-top: 0;
  padding: 0;
  color: #666;
  font-size: 14px;
  text-align: center;
}
</style>
