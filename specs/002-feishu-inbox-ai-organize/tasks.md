# 浠诲姟娓呭崟锛氶涔﹂殢璁板叆鍙ｄ笌 AI 鏀朵欢绠辩粺涓€鏁寸悊

> 鏂囨。璇█锛氶櫎浠ｇ爜鏍囪瘑绗︺€佸懡浠ゃ€佺幆澧冨彉閲忋€丄PI 璺緞銆侀敊璇爜鍜岀涓夋柟涓撴湁鍚嶈瘝澶栵紝鏈换鍔℃竻鍗曞繀椤讳娇鐢ㄤ腑鏂囨挵鍐欏苟褰掓。銆?**杈撳叆**锛氭潵鑷?`specs/002-feishu-inbox-ai-organize/` 鐨勮璁℃枃妗? 
**鍓嶇疆鏉′欢**锛歚plan.md`銆乣spec.md`銆乣research.md`銆乣data-model.md`銆乣contracts/feishu-inbox-contract.md`銆乣quickstart.md`

**娴嬭瘯瑕佹眰**锛氭湰鍔熻兘娑夊強椋炰功鎺ュ叆銆丄I 鏁寸悊銆佹暟鎹縼绉诲拰鍏变韩鍚庣琛屼负锛屽繀椤诲寘鍚嚜鍔ㄥ寲娴嬭瘯銆? 
**缁勭粐鏂瑰紡**锛氫换鍔℃寜鐢ㄦ埛鏁呬簨鍒嗙粍锛岀‘淇濇瘡涓晠浜嬪彲浠ョ嫭绔嬪疄鐜般€佺嫭绔嬫祴璇曞拰鐙珛婕旂ず銆?
## Phase 1锛氬噯澶囧伐浣滐紙鍏变韩鍩虹锛?
**鐩殑**锛氱‘璁ゅ綋鍓嶅垎鏀€佽鏍煎拰鐜版湁椋炰功/records 杈圭晫锛岄伩鍏嶅疄鐜板亸绂昏鍒掋€?
- [x] T001 纭褰撳墠鍒嗘敮涓?`002-feishu-inbox-ai-organize`锛屽苟闃呰 `specs/002-feishu-inbox-ai-organize/plan.md`
- [x] T002 [P] 闃呰鐜版湁椋炰功鍏ュ彛瀹炵幇骞惰褰曞奖鍝嶇偣锛歚server.py`銆乣feishu_client.py`
- [x] T003 [P] 闃呰鐜版湁 records 涓?AI 娴嬭瘯杈圭晫锛歚tests/test_records.py`銆乣tests/test_feishu.py`銆乣tests/test_feishu_client.py`

---

## Phase 2锛氬熀纭€璁炬柦锛堥樆濉炲墠缃級

**鐩殑**锛氬畬鎴愭墍鏈夌敤鎴锋晠浜嬪叡浜殑鏁版嵁妯″瀷銆佸箓绛夊瓧娈靛拰閫氱敤澶勭悊鍑芥暟銆?**鍏抽敭瑕佹眰**锛氭湰闃舵瀹屾垚鍓嶏紝涓嶅緱寮€濮嬩换浣曠敤鎴锋晠浜嬪疄鐜般€?
- [x] T004 鍦?`tests/test_records.py` 涓坊鍔?records 杩佺Щ娴嬭瘯锛岃鐩?`source`銆乣source_event_id`銆乣source_sender_json` 瀛楁
- [x] T005 鍦?`server.py` 鐨?records schema 鍜?migration 涓坊鍔?`source`銆乣source_event_id`銆乣source_sender_json` 瀛楁鍙婇涔︿簨浠跺幓閲嶇储寮?
- [x] T006 鍦?`server.py` 涓墿灞?`serialize_record_row`锛岃緭鍑?`source`銆乣sourceEventId`銆乣sourceSender` 瀛楁
- [x] T007 鍦?`server.py` 涓墿灞?`create_record`锛屾敮鎸佷紶鍏ユ潵婧愩€佹潵婧愪簨浠?ID銆佹潵婧愬彂閫佽€呬俊鎭苟淇濇寔 Web/PWA 榛樿鏉ユ簮涓?`web`
- [x] T008 鍦?`server.py` 涓柊澧為涔︽秷鎭厓鏁版嵁鎻愬彇宸ュ叿鍑芥暟锛岃鐩?message ID銆乻ender銆乧hat ID 鍜屾枃鏈被鍨嬪垽鏂?
- [x] T009 [P] 鍦?`tests/test_feishu.py` 涓坊鍔犻涔︽秷鎭?ID 鍜屽彂閫佽€呬俊鎭彁鍙栨祴璇?
**妫€鏌ョ偣**锛歳ecords 鏀寔鏉ユ簮鍏冩暟鎹紱Web/PWA 鍘熸湁 record 鍒涘缓璺緞涓嶅彉锛涢涔﹀叆鍙ｅ叿澶囧箓绛夋墍闇€鍩虹瀛楁銆?
---

## Phase 3锛氱敤鎴锋晠浜?1 - 椋炰功娑堟伅杩涘叆闅忚鏀朵欢绠憋紙P1锛孧VP锛?
**鐩爣**锛氶涔︽湁鏁堟枃鏈厛鍒涘缓鏉ユ簮涓洪涔︾殑 record锛屼笉鍐嶇洿鎺ュ垱寤烘寮忎换鍔°€?
**鐙珛娴嬭瘯**锛氬悜椋炰功浜嬩欢鍏ュ彛鍙戦€佹湁鏁堟枃鏈秷鎭悗锛宺ecords 涓嚭鐜版潵婧愪负椋炰功鐨勮褰曪紝todos 琛ㄦ病鏈夋柊澧炰换鍔★紱鍒锋柊 Web/PWA 鍙互鐪嬪埌璇ヨ褰曘€?
### 鐢ㄦ埛鏁呬簨 1 鐨勬祴璇?
- [x] T010 [P] [US1] 鍦?`tests/test_feishu.py` 涓坊鍔?HTTP 椋炰功浜嬩欢鍒涘缓 record 涓斾笉鍒涘缓 todo 鐨勬祴璇?
- [x] T011 [P] [US1] 鍦?`tests/test_feishu_client.py` 涓坊鍔犻暱杩炴帴 handler 鍒涘缓 record 涓斾笉璋冪敤鐩存帴寤轰换鍔℃棫璺緞鐨勬祴璇?
- [x] T012 [P] [US1] 鍦?`tests/test_records.py` 涓坊鍔?`GET /api/records` 杩斿洖椋炰功鏉ユ簮瀛楁鐨勬祴璇?
### 鐢ㄦ埛鏁呬簨 1 鐨勫疄鐜?
- [x] T013 [US1] 鍦?`server.py` 涓柊澧?`create_feishu_record` 鎴栫瓑浠峰嚱鏁帮紝鎸夐粯璁よ处鍙峰垱寤烘潵婧愪负 `feishu` 鐨?record
- [x] T014 [US1] 鍦?`server.py` 鐨?`/api/feishu/events` 璺緞涓敼涓鸿皟鐢ㄩ涔?record 鍒涘缓閫昏緫锛屼笉鍐嶇洿鎺ヨ皟鐢?`create_feishu_todo` 鎴?`create_feishu_ai_todos`
- [x] T015 [US1] 鍦?`feishu_client.py` 涓敼閫?`handle_feishu_event_payload`锛屽鐢ㄤ笌 HTTP 椋炰功鍏ュ彛涓€鑷寸殑 record 鍒涘缓閫昏緫
- [x] T016 [US1] 鍦?`server.py` 涓‘淇濋涔︾┖鏂囨湰銆侀潪鏂囨湰鍜岃秴闀挎枃鏈笉浼氬垱寤烘甯?record锛屽苟杩斿洖鍙帓鏌ョ姸鎬?
- [x] T017 [US1] 鍦?`web/app.js` 鍜?`web/index.html` 涓‘璁ゆ垨琛ュ厖闅忚鍒楄〃灞曠ず鏉ユ簮涓洪涔︾殑鏍囪瘑
- [x] T018 [US1] 鍦?`web/styles.css` 涓ˉ鍏呮潵婧愭爣璇嗘牱寮忥紝淇濇寔鐜版湁鐣岄潰瀵嗗害鍜屽彲璇绘€?
**妫€鏌ョ偣**锛氶涔︽秷鎭彲浠ョ嫭绔嬭繘鍏ラ殢璁版敹浠剁锛涙寮忎换鍔′笉浼氳嚜鍔ㄦ柊澧炪€?
---

## Phase 4锛氱敤鎴锋晠浜?2 - 椋炰功闅忚鑷姩鏁寸悊涓哄彲瀹℃煡缁撴灉锛圥1锛?
**鐩爣**锛氶涔?record 鍒涘缓鍚庣珛鍗虫墽琛?AI 鏁寸悊锛屾垚鍔?澶辫触閮戒繚鐣欏湪鍚屼竴鏉?record 涓婏紝骞跺悜椋炰功鍥炲鐘舵€併€?
**鐙珛娴嬭瘯**锛氬彂閫佸寘鍚换鍔″拰鏃ユ湡鐨勯涔︽秷鎭悗锛宺ecord 杩涘叆 `ready` 鎴?`failed` 鐘舵€侊紱鎴愬姛鏃惰繑鍥炰换鍔¤崏绋夸絾涓嶅垱寤烘寮忎换鍔★紱澶辫触鏃朵繚鐣欏師鏂囧拰閿欒銆?
### 鐢ㄦ埛鏁呬簨 2 鐨勬祴璇?
- [x] T019 [P] [US2] 鍦?`tests/test_feishu.py` 涓坊鍔?AI 鎴愬姛鏃堕涔?record 鏇存柊涓?`ready` 涓斾笉鍒涘缓 todo 鐨勬祴璇?
- [x] T020 [P] [US2] 鍦?`tests/test_feishu.py` 涓坊鍔?AI 鏈厤缃垨鏃犳晥 JSON 鏃?record 鏍囪 `failed` 鐨勬祴璇?
- [x] T021 [P] [US2] 鍦?`tests/test_feishu_client.py` 涓坊鍔犳垚鍔熷拰澶辫触閮界敓鎴愰涔﹀洖澶嶆枃妗堢殑娴嬭瘯

### 鐢ㄦ埛鏁呬簨 2 鐨勫疄鐜?
- [x] T022 [US2] 鍦?`server.py` 涓娊鍙?Web/PWA 鍜岄涔﹀叡鐢ㄧ殑 record AI 鏁寸悊鍑芥暟锛屽鐢?`call_xiaomi_record_organizer` 涓?`update_record_ai_result`
- [x] T023 [US2] 鍦?`server.py` 涓椋炰功浜嬩欢澶勭悊鍦ㄥ垱寤?record 鍚庣珛鍗宠皟鐢ㄥ叡鐢?AI 鏁寸悊鍑芥暟锛屽苟杩斿洖 `aiStatus`銆乣recordId` 鍜岄敊璇俊鎭?
- [x] T024 [US2] 鍦?`feishu_client.py` 涓牴鎹鐞嗙粨鏋滃洖澶嶉涔︽垚鍔熸垨澶辫触鐘舵€侊紝涓嶅啀鍙洖澶嶁€滄敹鍒扳€?
- [x] T025 [US2] 鍦?`server.py` 涓褰曢涔﹀鐞嗘棩蹇楋紝鍖呭惈 record ID銆丄I 鐘舵€佸拰 duplicate 鐘舵€侊紝涓斾笉寰楄緭鍑哄瘑閽?
- [x] T026 [US2] 鍦?`web/app.js` 涓‘璁ら涔?record 璇︽儏娌跨敤鐜版湁浠诲姟鑽夌瀹℃煡锛屼笉鑷姩淇濆瓨姝ｅ紡浠诲姟

**妫€鏌ョ偣**锛氶涔﹂殢璁板叿澶囦笌 Web/PWA 杈撳叆涓€鑷寸殑 AI 鏁寸悊缁撴灉锛涢涔︽敹鍒版垚鍔熸垨澶辫触鍙嶉銆?
---

## Phase 5锛氱敤鎴锋晠浜?3 - 浠庨涔﹁褰曠‘璁ょ敓鎴愭寮忎换鍔★紙P2锛?
**鐩爣**锛氱敤鎴峰湪 Web/PWA 涓粠椋炰功 record 鐨勪换鍔¤崏绋跨‘璁ゅ垱寤烘寮忎换鍔★紝骞朵繚鐣欐潵婧愯拷婧€?
**鐙珛娴嬭瘯**锛氶€夋嫨椋炰功 record 鐨勪换鍔¤崏绋夸繚瀛樺悗锛屾寮?todo 鍒涘缓鎴愬姛锛宍source_record_id` 鎸囧悜璇?record锛涙湭閫夋嫨鑽夌涓嶅垱寤轰换鍔°€?
### 鐢ㄦ埛鏁呬簨 3 鐨勬祴璇?
- [x] T027 [P] [US3] 鍦?`tests/test_records.py` 涓坊鍔犻涔︽潵婧?record 淇濆瓨浠诲姟鑽夌鍚庝繚鐣?`source_record_id` 鐨勬祴璇?
- [x] T028 [P] [US3] 鍦?`tests/test_records.py` 涓坊鍔犳潵婧?record 杞垹闄ゅ悗宸插垱寤?todo 浠嶅瓨鍦ㄥ苟鏄剧ず deleted 鏉ユ簮鐘舵€佺殑鍥炲綊娴嬭瘯

### 鐢ㄦ埛鏁呬簨 3 鐨勫疄鐜?
- [x] T029 [US3] 鍦?`server.py` 涓‘璁?`POST /api/records/{id}/todos` 瀵?`source = feishu` 鐨?record 璧扮幇鏈夌‘璁ゅ垱寤鸿矾寰?
- [x] T030 [US3] 鍦?`web/app.js` 涓‘璁ら涔︽潵婧?record 鐨勪换鍔¤崏绋块€夋嫨銆侀儴鍒嗕繚瀛樺拰鍏宠仈浠诲姟灞曠ず涓?Web 鏉ユ簮涓€鑷?
- [x] T031 [US3] 鍦?`web/index.html` 鍜?`web/styles.css` 涓ˉ鍏呮潵婧愯褰曡拷婧睍绀烘墍闇€鐨勬渶灏?UI 鏂囨鎴栨牱寮?
**妫€鏌ョ偣**锛氶涔﹁褰曡兘鍦?Web/PWA 涓浆涓烘寮忎换鍔★紱杩芥函鍏崇郴鍒锋柊鍚庝粛鍙銆?
---

## Phase 6锛氱敤鎴锋晠浜?4 - 閲嶅娑堟伅涓庡鐞嗙姸鎬侊紙P3锛?
**鐩爣**锛氬悓涓€椋炰功娑堟伅浜嬩欢 ID 閲嶅閫佽揪鏃朵笉鍒涘缓閲嶅 record锛屽苟鑳借〃杈惧鐞嗙姸鎬併€?
**鐙珛娴嬭瘯**锛氳繛缁彁浜や袱娆＄浉鍚岄涔︽秷鎭簨浠?ID锛屽彧浜х敓涓€鏉℃甯?record锛涚浜屾杩斿洖 duplicate 鐘舵€併€?
### 鐢ㄦ埛鏁呬簨 4 鐨勬祴璇?
- [x] T032 [P] [US4] 鍦?`tests/test_feishu.py` 涓坊鍔犵浉鍚岄涔︽秷鎭簨浠?ID 閲嶅閫佽揪鍙垱寤轰竴鏉?record 鐨勬祴璇?
- [x] T033 [P] [US4] 鍦?`tests/test_feishu_client.py` 涓坊鍔?duplicate 缁撴灉涓嶄細閲嶅鍥炲璇鎬ф垚鍔熸枃妗堢殑娴嬭瘯

### 鐢ㄦ埛鏁呬簨 4 鐨勫疄鐜?
- [x] T034 [US4] 鍦?`server.py` 涓疄鐜版寜 `source = feishu` 鍜?`source_event_id` 鏌ヨ宸叉湁 record 鐨勫箓绛夐€昏緫
- [x] T035 [US4] 鍦?`server.py` 涓閲嶅椋炰功浜嬩欢杩斿洖 `duplicate = true` 鍜屾棦鏈?`recordId`
- [x] T036 [US4] 鍦?`feishu_client.py` 涓鐞?duplicate 缁撴灉鐨勯涔﹀洖澶嶆枃妗?
- [x] T037 [US4] 鍦?`web/app.js` 涓‘璁ゆ敹浠剁鍒楄〃鍜岃鎯呰兘灞曠ず `pending`銆乣processing`銆乣ready`銆乣failed` 鐘舵€?
**妫€鏌ョ偣**锛氶噸澶嶉涔︿簨浠朵笉浼氭薄鏌撴敹浠剁锛涚敤鎴疯兘鐞嗚В娑堟伅澶勭悊鐘舵€併€?
---

## Phase 7锛氭墦纾ㄤ笌妯垏鍏虫敞鐐?
**鐩殑**锛氳ˉ榻愭枃妗ｃ€侀儴缃茶鏄庡拰鍏ㄩ噺楠岃瘉銆?
- [x] T038 [P] 鏇存柊 `README.md` 鐨勯涔︽満鍣ㄤ汉璇存槑锛岃鏄庨涔︽秷鎭繘鍏ラ殢璁版敹浠剁涓斾笉鐩存帴鍒涘缓姝ｅ紡浠诲姟
- [x] T039 [P] 鏇存柊 `docs/xiaomi-mimo-orbit-submission.md` 涓笌 AI/椋炰功鍏ュ彛鐩稿叧鐨勮鏄庯紝淇濇寔涓枃褰掓。
- [x] T040 妫€鏌?`deploy/todo-sync-feishu.service` 鏄惁浠嶆弧瓒虫湰杞幆澧冨彉閲忚姹傦紝蹇呰鏃舵洿鏂版敞閲婃垨 README 寮曞
- [x] T041 杩愯 `python -m py_compile server.py feishu_client.py`
- [x] T042 杩愯 `python -m unittest tests/test_feishu.py tests/test_feishu_client.py tests/test_records.py tests/test_ai_organizer.py`
- [ ] T043 鎸?`specs/002-feishu-inbox-ai-organize/quickstart.md` 鎵ц鎵嬪伐楠屾敹锛岃褰曠嚎涓婃垨鏈湴楠岃瘉缁撴灉

---

## 渚濊禆涓庢墽琛岄『搴?
### 闃舵渚濊禆

- **Phase 1 鍑嗗宸ヤ綔**锛氭棤渚濊禆锛屽彲浠ョ珛鍗冲紑濮嬨€?- **Phase 2 鍩虹璁炬柦**锛氫緷璧?Phase 1锛岄樆濉炴墍鏈夌敤鎴锋晠浜嬨€?- **Phase 3 鐢ㄦ埛鏁呬簨 1**锛氫緷璧?Phase 2锛屾槸 MVP銆?- **Phase 4 鐢ㄦ埛鏁呬簨 2**锛氫緷璧?Phase 3 鐨勯涔?record 鍒涘缓鑳藉姏銆?- **Phase 5 鐢ㄦ埛鏁呬簨 3**锛氫緷璧?Phase 3锛屽彲涓?Phase 4 鍚庡崐娈甸儴鍒嗗苟琛岋紝浣嗘渶缁堥獙鏀朵緷璧?AI 鑽夌鎴栨祴璇曟瀯閫犺崏绋裤€?- **Phase 6 鐢ㄦ埛鏁呬簨 4**锛氫緷璧?Phase 2 鐨勬潵婧愬瓧娈碉紝鍙湪 Phase 3 鍚庡苟琛屾帹杩涖€?- **Phase 7 鎵撶（**锛氫緷璧栨湰杞洰鏍囨晠浜嬪畬鎴愩€?
### 鐢ㄦ埛鏁呬簨渚濊禆

- **US1锛圥1锛?*锛氬熀纭€璁炬柦瀹屾垚鍚庡嵆鍙疄鐜帮紝鏄渶灏忓彲浜や粯銆?- **US2锛圥1锛?*锛氶渶瑕?US1 鐨勯涔?record 鍒涘缓璺緞銆?- **US3锛圥2锛?*锛氬鐢ㄧ幇鏈?records 纭浠诲姟璺緞锛岄渶瑕?US1 鐨勯涔︽潵婧?record銆?- **US4锛圥3锛?*锛氶渶瑕佹潵婧愪簨浠?ID 瀛楁鍜岄涔﹀叆鍙ｅ鐞嗚矾寰勩€?
### 鍗曚釜鐢ㄦ埛鏁呬簨鍐呴儴椤哄簭

- 娴嬭瘯鍏堝啓锛屽苟鍦ㄥ疄鐜板墠纭澶辫触銆?- 鏁版嵁杩佺Щ鍜屽簭鍒楀寲鍏堜簬浜嬩欢澶勭悊銆?- 鏈嶅姟绔鐞嗗厛浜庨涔﹀鎴风鍥炲銆?- Web/PWA 灞曠ず鍙仛鏀寔楠屾敹鎵€闇€鐨勬渶灏忔敼鍔ㄣ€?
### 鍙苟琛屾満浼?
- T002 鍜?T003 鍙苟琛岄槄璇讳笉鍚屾枃浠躲€?- T009 鍙笌 T005/T006 鍚庡崐娈靛苟琛屽噯澶囨祴璇曘€?- 鍚屼竴鏁呬簨涓殑娴嬭瘯浠诲姟閫氬父鍙苟琛岋紝浣嗗疄鐜?`server.py` 鐨勪换鍔￠渶瑕佷覆琛屾暣鍚堛€?- Web/PWA 灞曠ず浠诲姟 T017/T018銆乀030/T031 鍙湪鏈嶅姟绔瓧娈电ǔ瀹氬悗骞惰銆?- 鏂囨。浠诲姟 T038/T039 鍙笌鏈€缁堥獙璇佸噯澶囧苟琛屻€?
---

## 骞惰绀轰緥

### 鐢ㄦ埛鏁呬簨 1

```text
Task: "T010 鍦?tests/test_feishu.py 涓坊鍔?HTTP 椋炰功浜嬩欢鍒涘缓 record 涓斾笉鍒涘缓 todo 鐨勬祴璇?
Task: "T011 鍦?tests/test_feishu_client.py 涓坊鍔犻暱杩炴帴 handler 鍒涘缓 record 涓斾笉璋冪敤鐩存帴寤轰换鍔℃棫璺緞鐨勬祴璇?
Task: "T012 鍦?tests/test_records.py 涓坊鍔?GET /api/records 杩斿洖椋炰功鏉ユ簮瀛楁鐨勬祴璇?
```

### 鐢ㄦ埛鏁呬簨 2

```text
Task: "T019 鍦?tests/test_feishu.py 涓坊鍔?AI 鎴愬姛鏃堕涔?record 鏇存柊涓?ready 涓斾笉鍒涘缓 todo 鐨勬祴璇?
Task: "T020 鍦?tests/test_feishu.py 涓坊鍔?AI 鏈厤缃垨鏃犳晥 JSON 鏃?record 鏍囪 failed 鐨勬祴璇?
Task: "T021 鍦?tests/test_feishu_client.py 涓坊鍔犳垚鍔熷拰澶辫触閮界敓鎴愰涔﹀洖澶嶆枃妗堢殑娴嬭瘯"
```

### 鐢ㄦ埛鏁呬簨 4

```text
Task: "T032 鍦?tests/test_feishu.py 涓坊鍔犵浉鍚岄涔︽秷鎭簨浠?ID 閲嶅閫佽揪鍙垱寤轰竴鏉?record 鐨勬祴璇?
Task: "T033 鍦?tests/test_feishu_client.py 涓坊鍔?duplicate 缁撴灉涓嶄細閲嶅鍥炲璇鎬ф垚鍔熸枃妗堢殑娴嬭瘯"
```

---

## 瀹炴柦绛栫暐

### MVP 浼樺厛锛堝彧鍋氱敤鎴锋晠浜?1锛?
1. 瀹屾垚 Phase 1 鍜?Phase 2銆?2. 瀹屾垚 Phase 3锛岃椋炰功娑堟伅杩涘叆闅忚鏀朵欢绠变笖涓嶅垱寤烘寮忎换鍔°€?3. 杩愯 US1 鐩稿叧娴嬭瘯骞舵墜宸ョ‘璁?Web/PWA 鍙銆?
### 澧為噺浜や粯

1. US1锛氶涔︽崟鑾疯繘鍏?records銆?2. US2锛氶涔︽秷鎭珛鍗?AI 鏁寸悊骞跺洖澶嶇姸鎬併€?3. US3锛歐eb/PWA 浠庨涔?record 纭姝ｅ紡浠诲姟銆?4. US4锛氶涔︿簨浠?ID 鍘婚噸鍜岀姸鎬佸畬鍠勩€?5. Phase 7锛氭枃妗ｃ€侀儴缃茶鏄庡拰鍏ㄩ噺楠岃瘉銆?
### 瀹屾垚瀹氫箟

- 鎵€鏈変换鍔′娇鐢?checklist 鏍煎紡銆?- 鑷姩鍖栨祴璇曡鐩栭涔︽帴鍏ャ€丄I 鎴愬姛/澶辫触銆佸幓閲嶃€佹寮忎换鍔′笉鑷姩鍒涘缓鍜屾潵婧愯拷婧€?- `python -m py_compile server.py feishu_client.py` 閫氳繃銆?- 鎸囧畾 `unittest` 鍛戒护閫氳繃銆?- quickstart 鎵嬪伐楠屾敹鏃犲紓甯搞€?


