import type { GenreId } from '../music/genre';
import { GENRES } from '../music/genre';
import { RESEARCH_MEMES } from './memeKB';
import type { ResearchMeme } from './memeKB';

/**
 * Meme-to-Rave 梗库。
 *
 * 每条都是人工撰写的「梗 → 电子乐编制」映射，不是随机拼词：
 * 梗的情绪落点决定调式，梗的语速决定 BPM，梗的荒诞程度决定失真和密度。
 * 现场演示时，这一层负责"惊喜"，生成引擎负责"真的好听"。
 */

export interface MemeCard {
  id: string;
  name: string;
  emoji: string;
  keywords: string[];
  /** 这个梗在音乐上是什么 */
  concept: string;
  /** 一句话笑点，放界面标题下 */
  punchline: string;
  genreId: GenreId;
  bpm: number;
  /** 0-1 */
  density: number;
  /** 0-1 */
  energy: number;
  /** 0-1 */
  brightness: number;
  tags: string[];
  /** Drop 那一刻大屏上的字 */
  dropLine: string;
  /** 为什么这样写，讲给观众听 */
  why: string;
  /** 音色/织体提示 */
  palette: string;
  /** 以下为知识库溯源信息（可选） */
  sources?: string[];
  confidence?: 'high' | 'medium' | 'low';
  verified?: boolean;
  era?: string;
  category?: string;
  originNote?: string;
}

const CURATED_MEMES: MemeCard[] = [
  {
    id: 'zaoba',
    name: '早八打工人',
    emoji: '☕',
    keywords: ['早八', '打工人', '上班', '通勤', '闹钟', '打卡', '挤地铁', '起不来', '赖床', '起床', '赶时间'],
    concept: '被闹钟拽出被窝的那 3 秒，是一天里最像恐怖片的时刻',
    punchline: '闹钟响的那一刻，BPM 就已经定了',
    genreId: 'techno',
    bpm: 138,
    density: 0.86,
    energy: 0.88,
    brightness: 0.3,
    tags: ['techno', 'acid', '闹钟', '机械'],
    dropLine: '06:59 · 再睡五分钟',
    why: 'acid 的 16 分滚动就是闹钟的滴答；小调 + 低亮度对应天还没亮的地铁站',
    palette: 'acid bass + 四踩 + 冷色和弦刺',
  },
  {
    id: 'xianyanbao',
    name: '显眼包',
    emoji: '🦚',
    keywords: ['显眼包', '显眼', '社交', '出风头', '表演', '社牛'],
    concept: '全场最亮的那个人，音色也必须是最刺的那一个',
    punchline: '不是我抢镜，是我的 supersaw 太宽',
    genreId: 'electropop',
    bpm: 126,
    density: 0.8,
    energy: 0.82,
    brightness: 0.9,
    tags: ['electropop', 'supersaw', '大调', '亮'],
    dropLine: '让我来！',
    why: '大调 + 高亮度 + 方波主音，天生适合"求关注"；反拍和弦刺一响就有舞台感',
    palette: 'square lead + stab 反拍 + 明亮铺底',
  },
  {
    id: 'muyu',
    name: '电子木鱼',
    emoji: '🪵',
    keywords: ['木鱼', '电子木鱼', '功德', '敲', '佛系', '攒功德'],
    concept: '敲一下 +1 功德，所以节奏必须均匀到可以计数',
    punchline: '功德 +1，BPM +1',
    genreId: 'ambient',
    bpm: 92,
    density: 0.42,
    energy: 0.34,
    brightness: 0.42,
    tags: ['ambient', '留白', '重复', '治愈'],
    dropLine: '功德 +1',
    why: '稀疏的 8 分拨弦 + 长混响铺底，让"敲"这个动作变成冥想而不是舞曲',
    palette: 'pluck 8 分 + 宽铺底 + 大混响',
  },
  {
    id: 'maomao',
    name: '猫猫踩键盘',
    emoji: '🐱',
    keywords: ['猫', '猫猫', '踩键盘', '主子', '喵', '橘猫'],
    concept: '猫在键盘上走一圈，出来一段没人写得出的旋律',
    punchline: '它踩的不是键盘，是五声音阶',
    genreId: 'trap',
    bpm: 144,
    density: 0.72,
    energy: 0.66,
    brightness: 0.55,
    tags: ['trap', '808', '半拍', '跳跃'],
    dropLine: '喵。',
    why: 'trap 的 808 长音适合"猫步"的慵懒，16 分踩镲模仿爪子乱踩',
    palette: '808 + 铃铛主音 + 密集踩镲',
  },
  {
    id: 'pofang',
    name: '破防了',
    emoji: '💥',
    keywords: ['破防', '崩溃', '心态', '绷不住', 'emo', '难受'],
    concept: '破防不是一瞬间，是副歌前那两小节越积越满的和声',
    punchline: '我没事（正在做 32 分音符过门）',
    genreId: 'rock',
    bpm: 150,
    density: 0.92,
    energy: 0.95,
    brightness: 0.45,
    tags: ['rock', '失真', '过门', '爆发'],
    dropLine: '绷不住了',
    why: '失真锯齿 + 密集鼓点，把"忍"和"炸"的对比拉到最大',
    palette: 'distortion lead + 双踩 + 强力和弦',
  },
  {
    id: 'zhengdun',
    name: '整顿职场',
    emoji: '📎',
    keywords: ['整顿职场', '辞职', '老板', '职场', '画饼', '开会', '加班'],
    concept: '把辞职信拍在桌上的那一刻，需要一段军鼓滚奏',
    punchline: '这饼我不吃了，我改吃 Drop',
    genreId: 'dnb',
    bpm: 174,
    density: 0.9,
    energy: 0.9,
    brightness: 0.5,
    tags: ['dnb', 'breakbeat', 'reese', '高速'],
    dropLine: '我不干了',
    why: '174 BPM 的 breakbeat 天生有"夺门而出"的速度；reese 长贝斯压住阵脚',
    palette: 'reese bass + 碎裂鼓组 + 三角波主音',
  },
  {
    id: 'iren',
    name: 'i 人社交',
    emoji: '🫥',
    keywords: ['i人', '社恐', '内向', '聚会', '尴尬', '社交'],
    concept: '在人群里安静站着，脑子里却在放一整首 synthwave',
    punchline: '我不是冷场，我在等前奏结束',
    genreId: 'synthwave',
    bpm: 104,
    density: 0.52,
    energy: 0.44,
    brightness: 0.5,
    tags: ['synthwave', '复古', '宽', '独处'],
    dropLine: '（安静地站在角落）',
    why: '宽 supersaw + 慢起音，像霓虹灯牌在潮湿空气里晕开；BPM 慢，正好不用说话',
    palette: 'supersaw 铺底 + 拨弦贝斯 + 复古鼓',
  },
  {
    id: 'duoheshui',
    name: '多喝热水',
    emoji: '🥤',
    keywords: ['多喝热水', '直男', '关心', '敷衍', '感冒', '热水'],
    concept: '最万能也最敷衍的关心，配一个最万能也最敷衍的四踩',
    punchline: '关心是假的，四踩是真的',
    genreId: 'house',
    bpm: 122,
    density: 0.66,
    energy: 0.6,
    brightness: 0.6,
    tags: ['house', '四踩', '反拍', '稳'],
    dropLine: '多喝热水',
    why: 'house 的四踩永远不会出错，就像这句话永远可以回；反拍 sub 是那句"嗯嗯"',
    palette: '四踩 + 反拍 sub + stab',
  },
  {
    id: 'zhouyi',
    name: '周一早上的我',
    emoji: '🫠',
    keywords: ['周一', '星期一', '假期结束', '起床', '困'],
    concept: '灵魂还在周末，身体已经在工位——半拍错位的就是这个感觉',
    punchline: '人到了，魂没到',
    genreId: 'trap',
    bpm: 132,
    density: 0.58,
    energy: 0.5,
    brightness: 0.4,
    tags: ['trap', '半拍', '拖', '懒'],
    dropLine: '再睡五分钟',
    why: '半拍军鼓 + 拖长的 808，天然有"起不来"的迟滞感',
    palette: '808 长音 + 半拍军鼓 + 稀疏踩镲',
  },
  {
    id: 'kaoyan',
    name: '考研人',
    emoji: '📚',
    keywords: ['考研', '考试', '复习', '背书', '图书馆', '上岸'],
    concept: '倒计时牌翻页的声音，可以做成 riser',
    punchline: '倒计时 30 天，BPM 也已进入冲刺区',
    genreId: 'dnb',
    bpm: 168,
    density: 0.84,
    energy: 0.86,
    brightness: 0.6,
    tags: ['dnb', '冲刺', '推进', '明亮'],
    dropLine: '上岸！',
    why: '168 BPM 的推进感对应倒计时；明亮的主音是"会好的"那点希望',
    palette: 'breakbeat + pluck 主音 + 宽和弦',
  },
  {
    id: 'duche',
    name: '周一早高峰堵车',
    emoji: '🚗',
    keywords: ['堵车', '早高峰', '地铁', '挤', '迟到'],
    concept: '速度表和实际位移的巨大落差，就是这种"卡住的律动"',
    punchline: '我在动，只是地图上不动',
    genreId: 'techno',
    bpm: 128,
    density: 0.74,
    energy: 0.62,
    brightness: 0.36,
    tags: ['techno', '重复', '压抑', '工业'],
    dropLine: '前方 2 公里拥堵',
    why: 'techno 的重复和微小变化，正好表达"一直没动但一直在响"',
    palette: 'acid 滚动 + 工业鼓 + 冷铺底',
  },
  {
    id: 'shuangshiyi',
    name: '双十一凑单',
    emoji: '🛒',
    keywords: ['双十一', '凑单', '满减', '购物车', '剁手', '优惠券'],
    concept: '计算满减时的大脑，是一台 32 分音符的算术机器',
    punchline: '为了省 30，我多买了 300',
    genreId: 'electropop',
    bpm: 130,
    density: 0.88,
    energy: 0.8,
    brightness: 0.82,
    tags: ['electropop', '密集', '闪', '大调'],
    dropLine: '还差 12 元包邮',
    why: '高密度拨弦琶音模仿计算器连打；大调让"剁手"听起来很快乐',
    palette: '拨弦琶音 + 方波 + 亮鼓',
  },
  {
    id: 'jiqiren',
    name: 'AI 抢我饭碗',
    emoji: '🤖',
    keywords: ['AI', 'ai', '人工智能', '替代', '失业', '机器人', '模型'],
    concept: '被模型优化的恐惧，最适合用模型感的音色表达',
    punchline: '这篇稿子，是我和它一起写的',
    genreId: 'techno',
    bpm: 134,
    density: 0.8,
    energy: 0.72,
    brightness: 0.4,
    tags: ['techno', '机械', '未来', '冷'],
    dropLine: '正在生成……',
    why: '完全量化的 16 分音符 + 无摇摆，听起来就像机器在演奏',
    palette: '量化鼓组 + acid + 金属质感',
  },
  {
    id: 'zhengjiu',
    name: '深夜 emo',
    emoji: '🌙',
    keywords: ['深夜', 'emo', '失眠', '凌晨', '一个人', '想念'],
    concept: '凌晨三点，情绪比白天响 6 dB',
    punchline: '白天我是人，晚上我是混响',
    genreId: 'synthwave',
    bpm: 96,
    density: 0.46,
    energy: 0.3,
    brightness: 0.26,
    tags: ['synthwave', '慢', '大混响', '小调'],
    dropLine: '03:00',
    why: '小调 + 长混响 + 慢 BPM，把"一个人"的空间感做出来',
    palette: '宽铺底 + 弱主音 + 长衰减',
  },
  {
    id: 'sifeng',
    name: '司凤版整活',
    emoji: '🪩',
    keywords: ['司凤', '整活', '鬼畜', '抽象', '爆改', '魔改'],
    concept: '把一切严肃的东西高速播放，就变成了舞曲',
    punchline: '越离谱，越好蹦',
    genreId: 'sifeng',
    bpm: 172,
    density: 0.96,
    energy: 0.98,
    brightness: 0.55,
    tags: ['司凤版', '高速', '破音', '整活'],
    dropLine: '整！活！',
    why: '172 BPM + 失真主音 + 密集鼓，把"离谱"量化成可舞动的节奏',
    palette: 'grit 主音 + acid + 16 分踩镲',
  },
  {
    id: 'xiaban',
    name: '下班冲出公司',
    emoji: '🏃',
    keywords: ['下班', '冲', '跑', '解放', '六点', '打卡下班'],
    concept: '电梯门开的那一下，是全曲唯一的 drop',
    punchline: '18:00:01，我已经在楼下了',
    genreId: 'house',
    bpm: 128,
    density: 0.78,
    energy: 0.88,
    brightness: 0.72,
    tags: ['house', '四踩', '上扬', '快乐'],
    dropLine: '下班！！',
    why: '明亮大调 house，四踩一进来就是"解放"；反拍开镲是奔跑的脚步',
    palette: '四踩 + 开镲 + 亮 stab',
  },
];

/** 关键词越长越具体：按长度 1.5 次方加权，避免"挤"这种单字盖过"早八" */
function keywordWeight(k: string): number {
  return Math.pow(k.length, 1.5);
}

/** 研究知识库条目 → 梗卡（补齐风格画像里缺的参数） */
function cardFromResearch(r: ResearchMeme): MemeCard {
  const g = GENRES.find((x) => x.id === (r.style as GenreId));
  return {
    id: 'kb-' + r.id,
    name: r.name,
    emoji: r.emoji || '🎛️',
    keywords: r.keywords.length > 0 ? r.keywords : [r.name],
    concept: r.musicFit || r.context || r.usage,
    punchline: r.punchline || r.usage || r.name,
    genreId: (g ? g.id : 'meme_techno') as GenreId,
    bpm: r.bpm > 40 ? r.bpm : 128,
    density: g ? g.density : 0.8,
    energy: g ? Math.min(1, g.dynamics + 0.05) : 0.8,
    brightness: g ? g.brightness : 0.5,
    tags: [r.category, g ? g.name : r.style].filter(Boolean),
    dropLine: r.punchline || r.name,
    why: [r.originNote, r.context].filter(Boolean).join(' '),
    palette: r.timbre || 'synth + drums',
    sources: r.sources,
    confidence: r.confidence,
    verified: r.verified,
    era: r.era,
    category: r.category,
    originNote: r.originNote,
  };
}

/** 手工梗库 + 研究知识库；同名以手工条目为准 */
export const MEMES: MemeCard[] = (() => {
  const seen = new Set(CURATED_MEMES.map((m) => m.name));
  const extra: MemeCard[] = [];
  for (const r of RESEARCH_MEMES) {
    const card = cardFromResearch(r);
    if (seen.has(card.name)) continue;
    seen.add(card.name);
    extra.push(card);
  }
  return [...CURATED_MEMES, ...extra];
})();

function hash(text: string): number {
  let h = 2166136261;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

/**
 * 两级检索：
 *   1) 先查人工撰写的 16 条（编制映射更完整，生成的音乐更可控）；
 *   2) 没有命中，再查 42 条研究知识库（覆盖面广，用于新梗）。
 * 这样既不会丢掉质量，也不会因为"库里没有"而空手。
 */
export function findMemes(text: string, limit = 3): MemeCard[] {
  const t = text.trim().toLowerCase();
  if (!t) return [];

  const scoreOne = (card: MemeCard) => {
    let score = 0;
    for (const k of card.keywords) {
      const kk = k.toLowerCase();
      if (!t.includes(kk)) continue;
      score += keywordWeight(kk);
      const at = t.indexOf(kk);
      if (at >= 0 && at <= 6) score += 1.2;
    }
    if (t.includes(card.name.toLowerCase())) score += 10;
    return score;
  };

  const rank = (cards: MemeCard[]) =>
    cards
      .map((card) => ({ card, score: scoreOne(card) }))
      .filter((x) => x.score > 0)
      .sort((a, b) => b.score - a.score);

  const curated = rank(CURATED_MEMES);
  const research = rank(MEMES.filter((m) => m.id.startsWith('kb-')));
  const chosen = curated.length > 0 ? curated : research;
  return chosen.slice(0, limit).map((x) => x.card);
}

export function fallbackCard(text: string): MemeCard {
  const h = hash(text || 'meme');
  const genre = GENRES[h % GENRES.length];
  const bpm = 120 + (h % 40);
  const brightness = 0.3 + ((h >> 3) % 60) / 100;
  const density = 0.55 + ((h >> 7) % 40) / 100;
  const snippet = (text.trim() || '这段生活').slice(0, 16);
  return {
    id: `custom-${h.toString(36)}`,
    name: snippet,
    emoji: '🎛️',
    keywords: [snippet],
    concept: `把「${snippet}」直接当成一个声音事件：它有多具体，节奏就有多具体`,
    punchline: '你说的话，会变成一段可蹦的鼓',
    genreId: genre.id,
    bpm,
    density,
    energy: 0.5 + ((h >> 11) % 45) / 100,
    brightness,
    tags: [genre.name, ...genre.tags.slice(0, 2), '自定义梗'],
    dropLine: snippet,
    why: `按文本指纹选到 ${genre.name}（${bpm} BPM），因为它对这个长度的短句最不容易失控`,
    palette: genre.tags.slice(0, 3).join(' + '),
  };
}

/** 交给生成引擎的文本：把梗翻译成引擎认识的关键词 */
export function memeToPrompt(card: MemeCard): string {
  const genre = GENRES.find((g) => g.id === card.genreId) ?? GENRES[0];
  const moodWord =
    card.brightness > 0.62
      ? '开心 明亮 阳光'
      : card.brightness < 0.38
        ? '深夜 孤独 压抑'
        : '城市 赛博 夜色';
  const energyWord = card.energy > 0.7 ? '燃 冲 炸 高能' : card.energy < 0.4 ? '安静 温柔 轻' : '律动';
  return `${genre.name} ${genre.keywords[0] ?? ''} ${moodWord} ${energyWord} ${card.punchline} ${card.palette}`.trim();
}

export interface RaveStep {
  bar: number;
  label: string;
  line: string;
}

/** 课堂现场可照着念的 16 小节剧本 */
export function raveScript(card: MemeCard, bars = 16): RaveStep[] {
  const q = Math.max(1, Math.floor(bars / 4));
  return [
    { bar: 0, label: '前奏', line: `只有低频在动：「${card.name}」的呼吸` },
    { bar: q, label: '铺陈', line: `贝斯进场 · ${card.palette}` },
    { bar: q * 2, label: 'Build', line: '踩镲加密，主音收掉，只留 riser 往上顶' },
    { bar: q * 2 + Math.floor(q / 2), label: 'Drop 前 4 拍', line: '所有声部停住——等观众吸气' },
    { bar: q * 3 - 1, label: 'Drop', line: `「${card.dropLine}」` },
    { bar: q * 3, label: 'Break', line: card.why },
    { bar: bars - Math.max(1, Math.floor(q / 2)), label: '二次 Drop', line: '全编制回归，收尾' },
  ];
}
