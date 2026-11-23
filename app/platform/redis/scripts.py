"""Lua scripts run INSIDE Redis, so check-and-change happens atomically.

Without this, 200 simultaneous downloads of a "max 10" link could all read
count=9 and all succeed. A Lua script is executed as one indivisible step.
"""

# KEYS[1]=counter  ARGV[1]=max (0 = unlimited)  ARGV[2]=ttl seconds  ARGV[3]=seed
# Returns the new count, or -1 when the limit is already reached.
# `seed` self-heals the counter from Mongo if Redis lost the key (restart, eviction).
CLAIM_DOWNLOAD = """
local key  = KEYS[1]
local max  = tonumber(ARGV[1])
local ttl  = tonumber(ARGV[2])
local seed = tonumber(ARGV[3])
if redis.call('EXISTS', key) == 0 then
  redis.call('SET', key, seed, 'EX', ttl)
end
local current = tonumber(redis.call('GET', key))
if max > 0 and current >= max then
  return -1
end
return redis.call('INCR', key)
"""

# KEYS[1]=bucket key  ARGV[1]=window seconds. Fixed-window counter.
RATE_HIT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
  redis.call('EXPIRE', KEYS[1], tonumber(ARGV[1]))
end
return count
"""


class Scripts:
    def __init__(self, client) -> None:
        self.claim_download = client.register_script(CLAIM_DOWNLOAD)
        self.rate_hit = client.register_script(RATE_HIT)
