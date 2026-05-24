function qdiiAmountFormatter(nameVal, row){
  return '<a target="_blank" href="/data/fund/amount/' + row.fund_id + '">' + row.amount + '</a>';
}

function qdARStatusStyler(nameVal, row){
    var status = row[nameVal];
    if(status){
        if(status.includes('限')){
            return ';color:green;';
        }else if(status.includes('暂停')){
            return ';color:#999;';
        }
    }
    return '';
}

var tableQDIIA = null;
var bindQdiiStatusA = new AutoReloadStatus();
function showQDIIA(){
    var config ={
        dataURL: '/data/qdii/qdii_list/A',
        url_method: 'GET',
        tid: 'flex_qdiia',
        afterShow: bindQdiiAutoReloadA,
        cols: [
            {display: '代码', name:'fund_id', width:30, align:'center',
                link: {
                    url:'/data/qdii/detail/{{fund_id}}',
                    newpage: true,
                    type: self
                }
            },
            {display: '名称', name:'fund_nm_color', width:30, nowrap:true, align:'left'},
            {display: '现价', name:'price', width:40,tooltip: '更新时间：{{last_time}}', align:'right'},
            {display: '涨幅', name:'increase_rt', width:40, color:true, align:'right'},
            {display: '成交<br>(万元)', name:'volume', width:40, align:'right'},
            {display: '场内份额<br>(万份)', name:'amount', width:30, nowrap:true,tooltip: '{{amount_incr_tips}}', align:'right', formatter:qdiiAmountFormatter},
            {display: '场内新增<br>(万份)', name:'amount_incr', width:30, nowrap:true,tooltip: '{{amount_incr_tips}}', align:'right'},
            {display: 'IOPV', name:'iopv', title:'最新已公布的IOPV', tooltip: 'IOPV时间：{{iopv_dt}}', width:40, formatter:memberDataFormatter, nowrap:true, align:'right'},
            {display: 'IOPV<br>溢价率', name:'iopv_discount_rt', title:'现价对最新公布IOPV的溢价率', tooltip: 'IOPV时间：{{iopv_dt}}', width:40, color:true, formatter:memberPctDataFormatter, nowrap:true, align:'right'},

            {display: '净值', name:'fund_nav', width:40, nowrap:true, align:'right',
                link: {
                    url:'/data/qdii/detail/{{fund_id}}',
                    newpage: true,
                    type: self
                }
            },
            {display: '净值日期', name:'nav_dt', width:40, nowrap:true, align:'center'},
            {display: '净值<br>溢价率', name:'nav_discount_rt', title:'现价对最新已公布净值的溢价率', width:40, formatter:loginPctDataFormatter, nowrap:true, align:'right', color:true},
            {display: '指数涨幅', name:'ref_increase_rt', title:'相关指数的涨幅', width:40, nowrap:true,formatter:refIncreaseRtFormatter, align:'right'},
            {display: '相关指数', name:'index_nm', title:'相关跟踪/对标业绩的指数', width:100, nowrap:true, formatter:indexNameFormatter, align:'left'},

            {display: '估值', name:'estimate_value', width:40, tooltip: '估值时间：{{last_est_datetime}}', nowrap:true, formatter: estimateValueFormatter, align:'right',bgcolor:'#C0C0C0', hidden:!show_est_val},
            {display: '溢价率', name:'discount_rt', width:40,nowrap:true, formatter: discountRtFormatter, align:'right',bgcolor:'#C0C0C0', hidden:!show_est_val},
            
            {display: '申购费', name:'apply_fee', width:40,tooltip: '{{apply_fee_tips}}', nowrap:true, align:'right'},
            {display: '申购状态', name:'apply_status', formatter:loginDataFormatter, width:40, align:'right', nowrap:true, styler:qdARStatusStyler, sorter:'applyStatusSorter'},
            {display: '赎回费', name:'redeem_fee', width:40,tooltip: '{{redeem_fee_tips}}', nowrap:true, align:'right'},
            {display: '赎回状态', name:'redeem_status', width:40, align:'right', nowrap:true, styler:qdARStatusStyler},
            {display: '管托费', name:'mt_fee', title: '管理费+托管费', width:40,tooltip: '{{mt_fee_tips}}', percentage:true, nowrap:true, align:'right'},
            {display: '基金公司', name: 'issuer_nm', width:70, nowrap:true, formatter:issuerNameFormatter, align:'left'},
            {display: '操作', name: 'qdOpt',title: '操作', formatter: qdOptFormatter, width:15},
            {display: '最小单位', name:'min_amt', width:40, hidden: true},
            {display: '场内新增提示', name:'amount_incr_tips', width:40, hidden: true},
            {display: '申购费提示', name:'apply_fee_tips', width:40, hidden: true},
            {display: '赎回费提示', name:'redeem_fee_tips', width:40, hidden: true},
            {display: '管托费提示', name:'mt_fee_tips', width:40, hidden: true},
            {display: '最后更新', name: 'last_time', width:30,hidden: true},
            {display: 'IOPV时间', name:'iopv_dt', width:40, hidden: true},
            {display: '估算时间', name: 'last_est_datetime', width:30,hidden: true},
            { name: 'index_id', width:30,hidden: true}
        ],
        title: '亚洲指数(<a href="javascript:showQDIIA();">刷新</a>)&nbsp;&nbsp;&nbsp;&nbsp;<small>测试版，请谨慎参考！</small>&nbsp;&nbsp;&nbsp;&nbsp;' +
        '<span data-toggle="tooltip"><input id="auto_reload_qdiia"  type="checkbox" />30秒自动刷新</span>&nbsp;&nbsp;&nbsp;&nbsp;' +
        '<a href="/data/fund/amount/" target="_blank">场内基金份额查询器 <img src="/static/img/new.png"/></a>&nbsp;&nbsp;&nbsp;&nbsp;' + 
        '<form style="display: inline-block;" id="qdaSearchForm">' +
        '<label style="display:inline;margin-left:10px;"><input onclick="showQDIIA()" type="checkbox" name="only_owned" value="y">仅看自选</label>' +
        '<label style="display:inline;margin-left:20px;"><input onclick="showQDIIA()" type="checkbox" name="only_lof" value="y" checked>显示LOF</label>' +
        '<label style="display:inline;margin-left:5px;"><input onclick="showQDIIA()" type="checkbox" name="only_etf" value="y" checked>显示ETF</label>' +
        '</form>&nbsp;&nbsp;&nbsp;&nbsp;<a href="/question/454621" target="_blank" style="color:red;">ETF、跨境ETF申赎免费</a>&nbsp;&nbsp;&nbsp;&nbsp;' +
        '<a href="/question/68799" title="华宝香港中小盘(501021) FAQ" target="_blank">香港中小FAQ</a>'
    };
  if(!tableQDIIA){
    tableQDIIA = new SimpleTableBuilder(config);
    tableQDIIA.show();
  }else{
    if(G_USER_ID>0){
      var cnd = $('#qdaSearchForm').serializeObjectToJson();
      tableQDIIA.reload(cnd);
    }   
  }
}

function bindQdiiAutoReloadA(){
    setAutoReloadTable(tableQDIIA, 'auto_reload_qdiia','auto_reload_qdiia', showQDIIA, bindQdiiStatusA);
    if (!is_member){
        var list = $('[data-toggle="tooltip"]');
        list.attr('title','自动刷新购买会员可用');
        $('input',list).prop("checked",false);
    }
}

var tableQDIIE = null;
var bindQdiiStatusE = new AutoReloadStatus();
function showQDIIE(){
    var config ={
        dataURL: '/data/qdii/qdii_list/E',
        url_method: 'GET',
        tid: 'flex_qdiie',
        afterShow: bindQdiiAutoReloadE,
        cols: [
            {display: '代码', name:'fund_id', width:30, align:'center',
                link: {
                    url:'/data/qdii/detail/{{fund_id}}',
                    newpage: true,
                    type: self
                }
            },
            {display: '名称', name:'fund_nm_color', width:30, nowrap:true, align:'left'},
            {display: '现价', name:'price', width:40,tooltip: '更新时间：{{last_time}}', align:'right'},
            {display: '涨幅', name:'increase_rt', width:40, color:true, align:'right'},
            {display: '成交<br>(万元)', name:'volume', width:40, align:'right'},
            {display: '场内份额<br>(万份)', name:'amount', width:30, nowrap:true,tooltip: '{{amount_incr_tips}}', align:'right', formatter:qdiiAmountFormatter},
            {display: '场内新增<br>(万份)', name:'amount_incr', width:30, nowrap:true,tooltip: '{{amount_incr_tips}}', align:'right'},
            {display: 'IOPV', name:'iopv', title:'最新已公布的IOPV', tooltip: 'IOPV时间：{{iopv_dt}}', width:40, formatter:memberDataFormatter, nowrap:true, align:'right'},
            {display: 'IOPV<br>溢价率', name:'iopv_discount_rt', title:'现价对最新公布IOPV的溢价率', tooltip: 'IOPV时间：{{iopv_dt}}', width:40, color:true, formatter:memberPctDataFormatter, nowrap:true, align:'right'},

            {display: 'T-2净值', name:'fund_nav', width:40, nowrap:true, align:'right',
                link: {
                    url:'/data/qdii/detail/{{fund_id}}',
                    newpage: true,
                    type: self
                }
            },
            {display: '净值日期', name:'nav_dt_s', width:40, nowrap:true, sorter:'sortValue', sortValue:'nav_dt', align:'center'},

            {display: 'T-2净值<br>溢价率', name:'nav_discount_rt', formatter:loginPctDataFormatter, title:'现价对最新已公布净值的溢价率', width:40, nowrap:true, align:'right', color:true},
            {display: 'T-1指数涨幅', name:'ref_increase_rt', title:'相关指数T-1日的涨幅', width:40, nowrap:true, formatter:refIncreaseRtFormatter, align:'right'},
            {display: 'T-1盘后<br>期货涨幅', name:'us_increase_rt', title:'参考股指期货T-1盘后的期间涨幅', width:40, tooltip: '{{us_tips}}', nowrap:true, color:true, percentage:true, align:'right', formatter:memberPctDataFormatter,bgcolor:'#C0C0C0', hidden:!show_est_val},
            {display: '相关指数', name:'index_nm', title:'相关跟踪/对标的指数', width:100, nowrap:true, formatter:indexNameFormatter, align:'left'},

            {display: 'T-1估值', name:'estimate_value', width:40, tooltip: '估值时间：{{last_est_datetime}}', nowrap:true, formatter: estimateValueFormatter, align:'right',bgcolor:'#C0C0C0', hidden:!show_est_val},
            {display: '估值日期', name:'est_val_dt_s', width:40, nowrap:true, formatter: estValDtFormatter, sorter:'sortValue', sortValue:'est_val_dt', align:'center',bgcolor:'#C0C0C0', hidden:!show_est_val},
            {display: 'T-1溢价率', name:'discount_rt', width:40,nowrap:true, formatter: discountRtFormatter, align:'right',bgcolor:'#C0C0C0', hidden:!show_est_val},
            {display: '实时估值', name:'estimate_value2', width:40, nowrap:true, formatter: value2Formatter, align:'right',bgcolor:'#C0C0C0', hidden:!show_est_val},
            {display: '实时溢价率', name:'discount_rt2', width:40, nowrap:true, formatter: value2PctFormatter, align:'right',bgcolor:'#C0C0C0', hidden:!show_est_val},

            {display: '申购费', name:'apply_fee', width:40,tooltip: '{{apply_fee_tips}}', nowrap:true, align:'right'},
            {display: '申购状态', name:'apply_status', formatter:loginDataFormatter, width:40, align:'right', nowrap:true, styler:qdARStatusStyler, sorter:'applyStatusSorter'},
            {display: '赎回费', name:'redeem_fee', width:40,tooltip: '{{redeem_fee_tips}}', nowrap:true, align:'right'},
            {display: '赎回状态', name:'redeem_status', width:40, align:'right', nowrap:true, styler:qdARStatusStyler},
            {display: '管托费', name:'mt_fee', title: '管理费+托管费', width:40,tooltip: '{{mt_fee_tips}}', percentage:true, nowrap:true, align:'right'},
            {display: '基金公司', name: 'issuer_nm', width:70, nowrap:true, formatter:issuerNameFormatter, align:'left'},
            {display: '操作', name: 'qdOpt',title: '操作', formatter: qdOptFormatter, width:15},
            {display: '最小单位', name:'min_amt', width:40, hidden: true},
            {display: '场内新增提示', name:'amount_incr_tips', width:40, hidden: true},
            {display: '申购费提示', name:'apply_fee_tips', width:40, hidden: true},
            {display: '赎回费提示', name:'redeem_fee_tips', width:40, hidden: true},
            {display: '管托费提示', name:'mt_fee_tips', width:40, hidden: true},
            {display: '最后更新', name: 'last_time', width:30,hidden: true},
            {display: 'IOPV时间', name:'iopv_dt', width:40, hidden: true},
            {display: '估算时间', name: 'last_est_datetime', width:30,hidden: true},
            {display: '期间涨幅说明', name: 'us_tips', width:30,hidden: true},
            { name: 'index_id', width:30,hidden: true}
        ],
        title: '欧美指数(<a href="javascript:showQDIIE();">刷新</a>)&nbsp;&nbsp;&nbsp;&nbsp;<small>测试版，请谨慎参考！</small>&nbsp;&nbsp;&nbsp;&nbsp;' +
        '<span data-toggle="tooltip"><input id="auto_reload_qdiie"  type="checkbox" />30秒自动刷新</span>&nbsp;&nbsp;&nbsp;&nbsp;' +
        '<a href="/data/fund/amount/" target="_blank">场内基金份额查询器 <img src="/static/img/new.png"/></a>&nbsp;&nbsp;&nbsp;&nbsp;' + 
        '<form style="display: inline-block;" id="qdeSearchForm">' +
        '<label style="display:inline;margin-left:10px;"><input onclick="showQDIIE()" type="checkbox" name="only_owned" value="y">仅看自选</label>' +
        '<label style="display:inline;margin-left:20px;"><input onclick="showQDIIE()" type="checkbox" name="only_lof" value="y" checked>显示LOF</label>' +
        '<label style="display:inline;margin-left:5px;"><input onclick="showQDIIE()" type="checkbox" name="only_etf" value="y" checked>显示ETF</label>' +
        '</form>&nbsp;&nbsp;&nbsp;&nbsp;<a href="/question/454621" target="_blank" style="color:red;">ETF、跨境ETF申赎免费</a>&nbsp;&nbsp;&nbsp;&nbsp;'
    };
  if(!tableQDIIE){
    tableQDIIE = new SimpleTableBuilder(config);
    tableQDIIE.show();
  }else{
    if(G_USER_ID>0){
      var cnd = $('#qdeSearchForm').serializeObjectToJson();
      tableQDIIE.reload(cnd);
    }
  }
}

function bindQdiiAutoReloadE(){
    setAutoReloadTable(tableQDIIE, 'auto_reload_qdiie','auto_reload_qdiie', showQDIIE, bindQdiiStatusE);
    if (!is_member){
        var list = $('[data-toggle="tooltip"]');
        list.attr('title','自动刷新购买会员可用');
        $('input',list).prop("checked",false);
    }
}

var tableQDIIC = null;
var bindQdiiStatusC = new AutoReloadStatus();
var tableQDIICTitle = '商品(<a href="javascript:showQDIIC();">刷新</a>)&nbsp;&nbsp;&nbsp;&nbsp;<small>测试版，请谨慎参考！</small>&nbsp;&nbsp;&nbsp;&nbsp;<label style="display:inline;margin-left:10px;">' +
        '<span data-toggle="tooltip"><input id="auto_reload_qdiic" type="checkbox" />30秒自动刷新</span></label>&nbsp;&nbsp;&nbsp;&nbsp;' +
        '<a href="/data/fund/amount/" target="_blank">场内基金份额查询器 <img src="/static/img/new.png"/></a>&nbsp;&nbsp;&nbsp;&nbsp;' + 
        '<form style="display: inline-block;" id="qdcSearchForm">' +
        '<label style="display:inline;margin-left:10px;"><input onclick="showQDIIC()" type="checkbox" name="only_owned" value="y">仅看自选</label>' +
        '</form>&nbsp;&nbsp;&nbsp;&nbsp;<label style="display:inline;margin-left:10px;">';
if(show_est_val){
    tableQDIICTitle += '<input onclick="showQDIIC()" type="checkbox" id="show_oil" value="y">油气股QD实时估值</label><span style="color:red;font-size:8px;">切勿作为投资依据</span>&nbsp;&nbsp;&nbsp;&nbsp;';
}
tableQDIICTitle += '<a href="/question/454621" target="_blank" style="color:red;">ETF、跨境ETF申赎免费</a>&nbsp;&nbsp;&nbsp;&nbsp;' +
        '<a href="/question/62113" target="_blank">国泰商品FAQ</a>&nbsp;&nbsp;&nbsp;&nbsp;' +
        '<a href="/question/63575" target="_blank">华宝油气FAQ</a>&nbsp;&nbsp;&nbsp;&nbsp;' +
        '<a href="/question/64420" target="_blank">美国消费FAQ</a>&nbsp;&nbsp;&nbsp;&nbsp;';

function showQDIIC(){
    var config ={
        dataURL: '/data/qdii/qdii_list/C',
        url_method: 'GET',
        tid: 'flex_qdiic',
        afterShow: bindQdiiAutoReloadC,
        cols: [
            {display: '代码', name:'fund_id', width:30,
                link: {
                    url:'/data/qdii/detail/{{fund_id}}',
                    newpage: true,
                    type: self
                }
            },
            {display: '名称', name:'fund_nm_color', width:30, nowrap:true, align:'left'},
            {display: '现价', name:'price', width:40,tooltip: '更新时间：{{last_time}}', align:'right'},
            {display: '涨幅', name:'increase_rt', width:40, color:true, align:'right'},
            {display: '成交<br>(万元)', name:'volume', width:40, align:'right'},
            {display: '场内份额<br>(万份)', name:'amount', width:30, nowrap:true,tooltip: '{{amount_incr_tips}}', align:'right', formatter:qdiiAmountFormatter},
            {display: '场内新增<br>(万份)', name:'amount_incr', width:30, nowrap:true,tooltip: '{{amount_incr_tips}}', align:'right'},
            {display: 'T-2净值', name:'fund_nav', width:40, nowrap:true, align:'right',
                link: {
                    url:'/data/qdii/detail/{{fund_id}}',
                    newpage: true,
                    type: self
                }
            },
            {display: '净值日期', name:'nav_dt_s', width:40, nowrap:true, sorter:'sortValue', sortValue:'nav_dt', align:'center'},
            {display: 'T-2净值<br>溢价率', name:'nav_discount_rt', title:'现价对最新已公布净值的溢价率', width:40, percentage:true, nowrap:true, align:'right', color:true},
            {display: '相关标的/业绩比较', name:'index_nm', width:100, nowrap:true, align:'left'},
            {display: '参考标的<br>期间涨幅', name:'us_increase_rt', title:'参考标的的期间涨幅', width:40, tooltip: '{{us_tips}}', nowrap:true, color:true, percentage:true, align:'right', formatter:memberPctDataFormatter},

            {display: 'T-1估值', name:'estimate_value', width:40, tooltip: '估值时间：{{last_est_datetime}}', nowrap:true, align:'right',bgcolor:'#C0C0C0', hidden:!show_est_val},
            {display: '估值日期', name:'est_val_dt_s', width:40, nowrap:true, formatter: estValDtFormatter, sorter:'sortValue', sortValue:'est_val_dt', align:'center',bgcolor:'#C0C0C0', hidden:!show_est_val},
            {display: 'T-1溢价率', name:'discount_rt', width:40, nowrap:true, formatter: discountRtFormatter, align:'right',bgcolor:'#C0C0C0', hidden:!show_est_val},
            {display: '实时估值', name:'estimate_value2', width:40, nowrap:true, formatter: value2OilFormatter, styler: qtypecStyler, align:'right',bgcolor:'#C0C0C0', hidden:!show_est_val},
            {display: '实时溢价率', name:'discount_rt2', width:40, nowrap:true, formatter: value2OilPctFormatter, styler: qtypecStyler, align:'right',bgcolor:'#C0C0C0', hidden:!show_est_val},

            {display: '申购费', name:'apply_fee', width:40,tooltip: '{{apply_fee_tips}}', nowrap:true, align:'right'},
            {display: '申购状态', name:'apply_status', width:40, align:'right', nowrap:true, styler:qdARStatusStyler, sorter:'applyStatusSorter'},
            {display: '赎回费', name:'redeem_fee', width:40,tooltip: '{{redeem_fee_tips}}', nowrap:true, align:'right'},
            {display: '赎回状态', name:'redeem_status', width:40, align:'right', nowrap:true, styler:qdARStatusStyler},
            {display: '管托费', name:'mt_fee', title: '管理费+托管费', width:40,tooltip: '{{mt_fee_tips}}', percentage:true, nowrap:true, align:'right'},
            {display: '基金公司', name: 'issuer_nm', width:70, nowrap:true, formatter:issuerNameFormatter, align:'left'},
            {display: '操作', name: 'qdOpt',title: '操作', formatter: qdOptFormatter, width:15},

            {display: '最小单位', name:'min_amt', width:40, hidden: true},
            {display: '场内新增提示', name:'amount_incr_tips', width:40, hidden: true},
            {display: '申购费提示', name:'apply_fee_tips', width:40, hidden: true},
            {display: '赎回费提示', name:'redeem_fee_tips', width:40, hidden: true},
            {display: '管托费提示', name:'mt_fee_tips', width:40, hidden: true},
            {display: '最后更新', name: 'last_time', width:30,hidden: true},
            {display: '期间涨幅说明', name: 'us_tips', width:30,hidden: true},
            {display: '估算时间', name: 'last_est_datetime', width:30,hidden: true},
            { name: 'index_id', width:30,hidden: true}
        ],
        title: tableQDIICTitle
    };
  if(!tableQDIIC){
    tableQDIIC = new SimpleTableBuilder(config);
    tableQDIIC.show();
  }else{
    if(G_USER_ID>0){
      var cnd = $('#qdcSearchForm').serializeObjectToJson();
      tableQDIIC.reload(cnd);
    }
  }
}

function bindQdiiAutoReloadC(){
    setAutoReloadTable(tableQDIIC, 'auto_reload_qdiic','auto_reload_qdiic', showQDIIC, bindQdiiStatusC);
    if (!is_member){
        var list = $('[data-toggle="tooltip"]');
        list.attr('title','自动刷新购买会员可用');
        $('input',list).prop("checked",false);
    }
}

function showQDII(){
    showQDIIE();
    showQDIIC();
}

function is_oil2_qdii(fund_id){
    if(-1 !== $.inArray(fund_id, ['160216','163208', '160416', '162411', '162719', '165513', '161815'])){
        return true;
    }
    return false;
}

function is_oil_qdii(fund_id){
    if(-1 !== $.inArray(fund_id, ['501018', '160216', '161129', '160723', '163208', '160416', '162411', '162719', '165513', '161815'])){
        return true;
    }
    return false;
}

function qtypecStyler(nameVal, row){
    if(is_oil_qdii(row.fund_id)){
        return ';color:#ccc;font-style:italic';
    }
}

function value2OilFormatter(nameVal, row){
    var is_show_oil = $('#show_oil').prop("checked");
    if('buy' == row[nameVal]){
        return '<a href="/setting/member/" title="会员数据，点击购买会员" target="_blank">会员</a>';
    }else if('-' == row[nameVal] || '' == row[nameVal] || null == row[nameVal]){
        return '-';
    }else{
        if(!is_show_oil && is_oil2_qdii(row.fund_id)){
            return '<span title="如要查看请选中表头的【油气股QD实时估值】">-</span>';
        }else{
            var val = row[nameVal];
            if(row.cal_tips){
                val = '<span title="'+row.cal_tips+'">' + val + '</span>'
            }
            return val;
        }
    }
}

function value2OilPctFormatter(nameVal, row){
    var is_show_oil = $('#show_oil').prop("checked");
    var title = '';
    if(row.est_val_tm2){
        title = '更新时间: ' + row.est_val_tm2;
    }
    if(row.ref_price2 && row.ref_price2 != 'buy' && row.ref_price2 != ''){
        title += '   指数点位: ' + row.ref_price2;
    }
    if('buy' == row[nameVal]){
        return '<a href="/setting/member/" title="会员数据，点击购买会员" target="_blank">会员</a>';
    }else if('-' == row[nameVal] || '' == row[nameVal] || null == row[nameVal]){
        return '-';
    }else{
        var color = '#000';
        if(is_oil_qdii(row.fund_id)){
            color = '#ccc';
        }else if(parseFloat(row[nameVal]) > 0){
            color = 'red';
        }else if(parseFloat(row[nameVal]) < 0){
            color = 'green';
        }
        if(!is_show_oil && is_oil2_qdii(row.fund_id)){
            return '<span style="color:'+color+';">-</span>';
        }else{
            return '<span title="' + title + '" style="color:'+color+';">' + row[nameVal] + '%</span>';
        }
    }
}

function value2Formatter(nameVal, row){
    if('buy' == row[nameVal]){
        return '<a href="/setting/member/" title="会员数据，点击购买会员" target="_blank">会员</a>';
    }else if('-' == row[nameVal] || '' == row[nameVal] || null == row[nameVal]){
        return '-';
    }else{
        return '<span style="font-style:italic;color:#999;">' + row[nameVal] + '</span>';
    }
}

function value2PctFormatter(nameVal, row){
    var title = '';
    if(row.est_val_tm2){
        title = '更新时间: ' + row.est_val_tm2;
    }
    if(row.ref_price2 && row.ref_price2 != 'buy' && row.ref_price2 != ''){
        title += '   指数点位: ' + row.ref_price2;
    }
    if('buy' == row[nameVal]){
        return '<a href="/setting/member/" title="会员数据，点击购买会员" target="_blank">会员</a>';
    }else if('-' == row[nameVal] || '' == row[nameVal] || null == row[nameVal]){
        return '-';
    }else{
        var color = '#000';
        if(is_oil_qdii(row.fund_id)){
            color = '#ccc';
        }else if(parseFloat(row[nameVal]) > 0){
            color = 'red';
        }else if(parseFloat(row[nameVal]) < 0){
            color = 'green';
        }
        return '<span title="' + title + '" style="font-style:italic;color:'+color+';">' + row[nameVal] + '%</span>';
    }
}

function issuerNameFormatter(nameVal, row){
    if(row['issuer_nm']){
        if(row['urls']){
            return '<a target="_blank" rel="noopener noreferrer" href="' + row['urls'] + '">' + row['issuer_nm'] + '</a>';
        }
        return row['issuer_nm'];
    }
    return '';
}

function qdOptFormatter(nameVal, row){
    if(row.owned){
        return '<a title="将【' + row.fund_nm + '】从自选中删除" href="javascript:delOwnedQd(\'' + row.fund_id + '\');"><span class="jisilu-icons risered">&#xe61d;</span></a>';
    }else{
        return '<a title="将【' + row.fund_nm + '】添加入自选" href="javascript:addOwnedQd(\'' + row.fund_id + '\');"><span class="jisilu-icons">&#xe61e;</span></a>';
    }
}

function reloadActiveTable(){
    if($('#tlink_qdiie').parent().hasClass('active')){
        showQDIIE();
        showQDIIC();
    }else if($('#tlink_qdiia').parent().hasClass('active')){
        showQDIIA();
    }
}

function addOwnedQd(fund_id){
    $.post(G_BASE_URL + '/data/qdii/add_owned_qd/',{fund_id : fund_id},function(rst){
        if(!rst.isError){
            reloadActiveTable();
        }else{
            $.alert(rst.msg);
        }
    },'json');
}
function delOwnedQd(fund_id){
    $.post(G_BASE_URL + '/data/qdii/del_owned_qd/',{fund_id : fund_id},function(rst){
        if(!rst.isError){
            reloadActiveTable();
        }else{
            $.alert(rst.msg);
        }
    },'json');
}

function estimateValueFormatter(nameVal, row){
    if('QDII' == row.lof_type && row.notes){
        return '<span title="'+row.notes+' T-1估值:'+row.estimate_value+'"> - </span>';
    }else if('CNY' == row.money_cd){
        if('E' == row.qtype){
            return '<span title="人民币计价指数">' + row.estimate_value + '</span>';
        }else{
            return '<span title="未考虑汇率波动，请谨慎参考！" style="font-style:italic;color:#999;">' + row.estimate_value + '</span>';
        }
    }else if('HKD' == row.money_cd){
        return '<span title="估值按港币中间价进行调整">' + row.estimate_value + '</span>';
    }else if('USD' == row.money_cd){
        return '<span title="估值按美元中间价进行调整">' + row.estimate_value + '</span>';
    }else if('EUR' == row.money_cd){
        return '<span title="估值按欧元中间价进行调整">' + row.estimate_value + '</span>';
    }else{
        return row.estimate_value;
    }
}

function estValDtFormatter(nameVal, row){
    if('QDII' == row.lof_type && row.notes){
        return '<span title="'+row.notes+' 估值日期:'+row.est_val_dt_s+'"> - </span>';
    }else{
        return row.est_val_dt_s;
    }
}

function estValIncreaseRtFormatter(nameVal, row){
    if('QDII' == row.lof_type && row.notes){
        return '<span title="'+row.notes+' 估值涨幅:'+row.est_val_increase_rt+'"> - </span>';
    }else{
        if(parseFloat(row.est_val_increase_rt) > 0){
            return '<span style="color:red">' + row.est_val_increase_rt + '</span>';
        }else if(parseFloat(row.est_val_increase_rt) < 0){
            return '<span style="color:green">' + row.est_val_increase_rt + '</span>';
        }else{
            return row.est_val_increase_rt;
        }
    }
}

function discountRtFormatter(nameVal, row){
    var title = '';
    if(row.last_time && row.est_val_dt){
        title = '更新时间：' + row.est_val_dt + ' ' + row.last_time;
    }
    if(row.notes){
        title += " " + row.notes;
    }
    
    if(parseFloat(row.discount_rt) > 0){
        return '<span title="'+title+'" style="color:red">' + row.discount_rt + '</span>';
    }else if(parseFloat(row.discount_rt) < 0){
        return '<span title="'+title+'" style="color:green">' + row.discount_rt + '</span>';
    }else{
        return '<span title="'+title+'">' + row.discount_rt + '</span>';
    }
}

function indexNameFormatter(nameVal, row){
    var title_info = '';
    var style_val = '';
    if('N' == row.index_id){
        style_val = 'font-style:italic;filter:alpha(opacity=30);opacity:0.3;';
    }
    return '<span style="' + style_val + '" title="' + title_info + '">' + row.index_nm + '</span>';
}

function refIncreaseRtFormatter(nameVal, row){
    if(0 == G_USER_ID){
        return '<a title="该数据需要登录查看" href="/login/">登录</a>';
    }
    var ref_increase_rt_val = parseFloat(row.ref_increase_rt);
    var title_info = '指数更新日期: ' + row.est_val_dt;
    if(row.ref_price){
        title_info += '   点位: ' + row.ref_price;
    }
    var style_val = '';
    if(!row.index_id){
        title_info = '主动基金，重仓涨幅';
        style_val = 'font-style:italic;filter:alpha(opacity=30);opacity:0.3;';
    }
    if(ref_increase_rt_val > 0){
        style_val += 'color:red;';
    }else if(ref_increase_rt_val < 0){
        style_val += 'color:green;';
    }
    if(row.cal_tips){
        title_info = row.cal_tips;
    }
    return '<span style="' + style_val + '" title="' + title_info + '">' + row.ref_increase_rt + '</span>';
}
