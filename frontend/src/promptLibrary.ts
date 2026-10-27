/** 十五项党务功能的 AI 助手提示词案例库。 */

export interface PromptCase {
  title: string;
  prompt: string;
  /** orchestration = 填入顶部跨模块编排框；draft = 填入下方只读草稿具体要求 */
  target: "orchestration" | "draft";
}

export interface PromptFeature {
  id: string;
  feature: string;
  cases: PromptCase[];
}

export const PROMPT_LIBRARY: PromptFeature[] = [
  {
    id: "development",
    feature: "党员发展全流程管理",
    cases: [
      {
        title: "入党申请建档（自动生成全流程时间轴）",
        prompt: "张明远今天递交了入党申请书，请纳入发展党员管理",
        target: "orchestration",
      },
      {
        title: "带日期与支部的建档",
        prompt: "李文博于2026年11月3日递交入党申请书，纳入发展党员管理，第二党支部",
        target: "orchestration",
      },
      {
        title: "测算已有档案的时间轴",
        prompt: "帮我测算白圆的发展党员时间轴，列出各节点法定依据",
        target: "orchestration",
      },
    ],
  },
  {
    id: "education",
    feature: "党员教育管理",
    cases: [
      {
        title: "登记集中培训",
        prompt: "组织党的二十届四中全会精神集中培训，16学时，45人参加，机关党支部承办",
        target: "orchestration",
      },
      {
        title: "登记在线学习",
        prompt: "登记一期党纪学习教育在线学习，12学时，第三党支部组织",
        target: "orchestration",
      },
    ],
  },
  {
    id: "standardization",
    feature: "党支部标准化规范化建设",
    cases: [
      {
        title: "对标自查结果登记",
        prompt: "登记第一党支部标准化对标自查：组织生活类，三会一课按期规范开展，达标",
        target: "orchestration",
      },
      {
        title: "不达标事项登记（会进入整改跟踪）",
        prompt: "登记第二党支部标准化对标自查：功能作用类，党建与业务融合载体建设，不达标，整改措施是建立党员责任区",
        target: "orchestration",
      },
    ],
  },
  {
    id: "meetings",
    feature: "“三会一课”与主题党日",
    cases: [
      {
        title: "建立会议草稿并生成筹备流程",
        prompt: "下周三召开支部党员大会，议题是讨论接收预备党员，请建立会议草稿并生成筹备流程",
        target: "orchestration",
      },
      {
        title: "主题党日筹备",
        prompt: "本月开展主题党日活动，主题是重温入党誓词，请建立会议草稿并生成六步筹备流程",
        target: "orchestration",
      },
    ],
  },
  {
    id: "review",
    feature: "组织生活会与民主评议党员",
    cases: [
      {
        title: "民主评议结果登记",
        prompt: "登记2026年度民主评议：第二党支部刘晓峰，自评合格，互评合格，组织定格合格，已完成",
        target: "orchestration",
      },
      {
        title: "带问题与整改的评议",
        prompt: "登记2026年度民主评议：第三党支部赵铁军，自评合格，互评基本合格，组织定格基本合格，查摆问题是理论学习不够系统，整改措施是制定每周学习计划",
        target: "orchestration",
      },
    ],
  },
  {
    id: "fees",
    feature: "党费收缴使用管理",
    cases: [
      {
        title: "登记党费收缴",
        prompt: "登记王国辉的10月党费100元",
        target: "orchestration",
      },
      {
        title: "登记党费使用支出",
        prompt: "登记一笔党费使用：党员教育培训资料购置1500元，审批人党委组织部",
        target: "orchestration",
      },
    ],
  },
  {
    id: "statistics",
    feature: "党内统计与党员信息管理",
    cases: [
      {
        title: "新增党员入册",
        prompt: "新增党员陈立群，男，第三党支部，2020年7月1日入党，大学本科学历，正式党员",
        target: "orchestration",
      },
      {
        title: "党员信息更新（预备转正）",
        prompt: "新增党员吴志强信息更新：转为正式党员，入党时间2026年6月28日",
        target: "orchestration",
      },
    ],
  },
  {
    id: "assessment",
    feature: "党建工作责任制考核",
    cases: [
      {
        title: "新增考核指标",
        prompt: "新增2026年责任制考核指标：作风建设类，联系服务群众成效，分值10分，责任部门各党支部",
        target: "orchestration",
      },
      {
        title: "政治建设类指标",
        prompt: "新增责任制考核指标：政治建设类，第一议题制度落实情况，分值15分，责任部门党委办公室",
        target: "orchestration",
      },
    ],
  },
  {
    id: "documents",
    feature: "党务文书起草与审核",
    cases: [
      {
        title: "起草通知（先在下方选择相关任务或文件）",
        prompt: "根据所选事项和材料，起草一份关于开展主题党日活动的通知，按公文格式组织，包含时间、地点、参加人员和要求",
        target: "draft",
      },
      {
        title: "材料审核把关",
        prompt: "检查所选事项的材料清单，指出可能缺项，并按公文规范给出补正建议",
        target: "draft",
      },
    ],
  },
  {
    id: "propaganda",
    feature: "党建宣传与思想政治工作策划",
    cases: [
      {
        title: "宣传活动方案策划",
        prompt: "结合本月三会一课安排，策划一份学习贯彻党的二十届四中全会精神的宣传方案，包含主题、形式、时间安排和责任人建议",
        target: "draft",
      },
      {
        title: "思想政治工作计划",
        prompt: "针对大修期间职工压力偏大的情况，起草一份思想政治工作方案，包含谈心谈话安排、关心关爱措施和支部责任分工",
        target: "draft",
      },
    ],
  },
  {
    id: "opinion",
    feature: "舆情监测",
    cases: [
      {
        title: "舆情登记",
        prompt: "登记一条舆情：微信渠道有职工反映食堂排队时间过长，程度一般，责任人工会，处置状态登记",
        target: "orchestration",
      },
      {
        title: "舆情办结登记",
        prompt: "登记一条舆情：网站留言咨询职称评审政策，程度一般，已办结，责任人人力资源部",
        target: "orchestration",
      },
    ],
  },
  {
    id: "union",
    feature: "工会活动策划",
    cases: [
      {
        title: "工会活动登记",
        prompt: "举办金秋职工趣味运动会，10月28日在文体中心举行，120人参加，预算5000元，工会承办",
        target: "orchestration",
      },
      {
        title: "慰问活动登记",
        prompt: "开展困难职工走访慰问活动，11月2日入户走访，8户家庭，预算4000元，工会承办",
        target: "orchestration",
      },
    ],
  },
  {
    id: "election",
    feature: "团组织换届",
    cases: [
      {
        title: "换届记录登记",
        prompt: "登记第三团支部第十三届换届，2026年11月5日进行，新任书记王梦洁，已报批",
        target: "orchestration",
      },
      {
        title: "待报批换届",
        prompt: "登记第二团支部第十二届换届，新任书记何嘉俊，待报批",
        target: "orchestration",
      },
    ],
  },
  {
    id: "league",
    feature: "团员管理",
    cases: [
      {
        title: "新团员入册",
        prompt: "收到团员徐嘉的入团申请，纳入团员名册，第一团支部",
        target: "orchestration",
      },
      {
        title: "团员信息完善",
        prompt: "新增团员唐思琪，女，第二团支部，大学本科，在册",
        target: "orchestration",
      },
    ],
  },
  {
    id: "brand",
    feature: "文化品牌",
    cases: [
      {
        title: "党建品牌入库",
        prompt: "新增党建品牌「红色引擎」，口号是攻坚克难当先锋，由检修党支部培育",
        target: "orchestration",
      },
      {
        title: "文化品牌入库",
        prompt: "新增文化品牌「核城故事」，口号是讲好核城故事传承红色基因，由党委宣传部培育",
        target: "orchestration",
      },
    ],
  },
];
