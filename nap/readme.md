## CPUIdle Governor Comparison (60s Screen-Off Test)

| CPU | `nap` | `mtk_menu` | Better |
|:---:|:------|:-----------|:-------|
| CPU0 | rgidle: **7162 ms** (1943)<br>mcdi: **51862 ms** (2614) | rgidle: **4234 ms** (4803)<br>mcdi: **50946 ms** (5710) | **nap** — Longer idle residency with significantly fewer wakeups. |
| CPU1 | rgidle: **7225 ms** (3220)<br>mcdi: **51546 ms** (3512) | rgidle: **4022 ms** (4821)<br>mcdi: **51774 ms** (4846) | **nap** — Similar residency, but much lower idle transitions. |
| CPU2 | rgidle: **7070 ms** (2557)<br>mcdi: **51847 ms** (2687) | rgidle: **3968 ms** (4470)<br>mcdi: **51329 ms** (5969) | **nap** — Longer idle time and fewer wakeups. |
| CPU3 | rgidle: **7086 ms** (1985)<br>mcdi: **52187 ms** (1552) | rgidle: **3349 ms** (3946)<br>mcdi: **53238 ms** (3438) | **nap** — Lower wakeup count despite similar deep idle residency. |
| CPU4 | rgidle: **7192 ms** (1770)<br>mcdi: **52329 ms** (1812) | rgidle: **3702 ms** (3407)<br>mcdi: **52202 ms** (5152) | **nap** — Much fewer idle entries while maintaining comparable residency. |
| CPU5 | rgidle: **7303 ms** (1834)<br>mcdi: **51930 ms** (1506) | rgidle: **3223 ms** (2742)<br>mcdi: **53262 ms** (3355) | **nap** — Lower transition count with similar overall idle time. |
| CPU6 | rgidle: **7124 ms** (3646)<br>mcdi: **51408 ms** (3183) | rgidle: **5109 ms** (8737)<br>mcdi: **49263 ms** (8387) | **nap** — Considerably fewer wakeups and longer idle residency. |
| CPU7 | rgidle: **7126 ms** (4637)<br>mcdi: **51759 ms** (3380) | rgidle: **4596 ms** (7037)<br>mcdi: **49901 ms** (7944) | **nap** — Nearly half the wakeups while spending more time idle. |

> Values in parentheses represent the number of idle state entries (`usage`). Lower values generally indicate fewer wakeups and reduced idle transition overhead.
>
> 
### Summary

| Metric | `nap` | `mtk_menu` | Winner |
|:-------|:------|:-----------|:------:|
| Average `rgidle` residency | ~7.16 s | ~4.03 s | ✅ `nap` |
| Average `mcdi` residency | ~51.9 s | ~51.0 s | ✅ `nap` |
| Idle transition count (`usage`) | Lower | Higher | ✅ `nap` |
| Wakeup frequency | Lower | Higher | ✅ `nap` |
| Standby efficiency | Better | Good | ✅ `nap` |

**Conclusion:** Under a 60-second screen-off idle test, **`nap` consistently achieves longer idle residency while requiring fewer idle state transitions than `mtk_menu`**. This suggests lower wakeup overhead and potentially better power efficiency during standby.
