/**
 * 场景任务模板。
 * 设计要点：不同拍摄对象需要"采集的信息"完全不同，
 * 用模板把"泛泛描述"收敛成"该场景必须回答的字段"，
 * 缺字段就触发重拍引导——这是本作品与普通图像描述工具的核心差异。
 */

const SCENES = {
  medicine: {
    label: '药品',
    required: ['药名', '规格', '用法用量', '禁忌或注意事项'],
    answerFocus: '一次几片、一日几次、饭前还是饭后、什么人不能吃',
    risk: 'high',
    retakeHints: {
      missing_back: '这面只有药名。请把药盒翻过来，拍带有用法用量和禁忌的那一面。',
      too_far: '字看不清，请把手机靠近一些，大约一拃的距离，再拍一次。',
      too_close: '太近了，画面里只有几个字。请把手机拿远一点，让整块说明都在画面里。',
      blur: '照片有点糊，请把手机拿稳，停一秒再拍。'
    }
  },
  express: {
    label: '快递单',
    required: ['取件码或运单号', '驿站或柜机名称'],
    answerFocus: '取件码是多少、去哪取、什么时候前取走',
    risk: 'low',
    retakeHints: {
      missing_code: '没看到取件码。请对准快递单上有条码的那一面。',
      too_far: '取件码看不清，请靠近一点再拍。',
      blur: '照片模糊，请拿稳后再拍一次。'
    }
  },
  menu: {
    label: '菜单',
    required: ['菜名', '价格'],
    answerFocus: '有哪些菜、多少钱、有没有辣的',
    risk: 'low',
    retakeHints: {
      too_far: '菜名太小了，请靠近菜单或者分段拍。',
      blur: '照片糊了，请拿稳手机，等对焦好再拍。'
    }
  },
  unknown: {
    label: '其他物品',
    required: [],
    answerFocus: '这是什么、有什么值得注意的信息',
    risk: 'low',
    retakeHints: {
      too_far: '看不清细节，请靠近一些。',
      blur: '照片有点糊，请拿稳再拍一次。'
    }
  }
};

const SYSTEM_PROMPT = `你是一个为视障人士服务的视觉问答助手。用户拍了一张照片，可能附带一句语音提问。

你的任务分两步，且必须严格按下面的顺序：

第一步，判断这张照片是否"可用于回答"：
- 画面是否完整（主体是否被裁掉）
- 是否清晰（是否明显失焦、抖动模糊）
- 就场景所需的关键信息而言，是否已经拍到了（例如药品需要看到用法用量，快递单需要看到取件码）
- 如果该物品的关键信息在另一面，明确提示用户翻面重拍。

第二步，只有在信息足够时才生成回答；否则只输出重拍引导，不要猜测、不要编造。

硬性规则：
1. 绝不编造图中不存在的信息。图中没有写的内容，一律不回答。
2. 涉及药品时，只复述图中原文给出的用法用量，并附一句"具体用药请与药师或医生确认"。不做剂量推断，不给治疗建议。
3. 回答必须短、必须可执行。先给结论，再给一句依据。不要念整页说明书。
4. 用第二人称、口语化中文，适合语音播报，避免括号、星号、表格等符号。

必须只输出以下 JSON，不要输出任何其他文字：
{
  "ok": true 或 false,
  "scene": "medicine" | "express" | "menu" | "unknown",
  "quality": { "blur": true/false, "cropped": true/false, "too_far": true/false, "too_close": true/false, "angle": true/false },
  "missing": ["缺失的信息项，中文短语"],
  "hint": "当 ok 为 false 时，给用户的一句具体调整指令；ok 为 true 时为空字符串",
  "answer": "当 ok 为 true 时的口语化回答；ok 为 false 时为空字符串",
  "evidence": "回答依据的图中原文片段，用于核查是否编造"
}`;

module.exports = { SCENES, SYSTEM_PROMPT };
