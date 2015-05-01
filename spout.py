import optparse, time
from qpid.messaging import *
from qpid.util import URL
from qpid.log import enable, DEBUG, WARN

def nameval(st):
  idx = st.find("=")
  if idx >= 0:
    name = st[0:idx]
    value = st[idx+1:]
  else:
    name = st
    value = None
  return name, value

parser = optparse.OptionParser(usage="usage: %prog [options] ADDRESS [ CONTENT ... ]",
                               description="Send messages to the supplied address.")
parser.add_option("-b", "--broker", default="localhost",
                  help="connect to specified BROKER (default %default)")
parser.add_option("-r", "--reconnect", action="store_true",
                  help="enable auto reconnect")
parser.add_option("-i", "--reconnect-interval", type="float", default=3,
                  help="interval between reconnect attempts")
parser.add_option("-l", "--reconnect-limit", type="int",
                  help="maximum number of reconnect attempts")
parser.add_option("-c", "--count", type="int", default=1,
                  help="stop after count messages have been sent, zero disables (default %default)")
parser.add_option("-t", "--timeout", type="float", default=None,
                  help="exit after the specified time")
parser.add_option("-I", "--id", help="use the supplied id instead of generating one")
parser.add_option("-S", "--subject", help="specify a subject")
parser.add_option("-R", "--reply-to", help="specify reply-to address")
parser.add_option("-P", "--property", dest="properties", action="append", default=[],
                  metavar="NAME=VALUE", help="specify message property")
parser.add_option("-M", "--map", dest="entries", action="append", default=[],
                  metavar="KEY=VALUE",
                  help="specify map entry for message body")
parser.add_option("-v", dest="verbose", action="store_true",
                  help="enable logging")

opts, args = parser.parse_args()

if opts.verbose:
  enable("qpid", DEBUG)
else:
  enable("qpid", WARN)

if opts.id is None:
  spout_id = str(uuid4())
else:
  spout_id = opts.id
if args:
  addr = args.pop(0)
else:
  parser.error("address is required")

content = None

if args:
  text = " ".join(args)
else:
  text = None

if opts.entries:
  content = {}
  if text:
    content["text"] = text
  for e in opts.entries:
    name, val = nameval(e)
    content[name] = val
else:
  content = text

conn = Connection(opts.broker,
                  reconnect=opts.reconnect,
                  reconnect_interval=opts.reconnect_interval,
                  reconnect_limit=opts.reconnect_limit)
try:
  conn.open()
  ssn = conn.session()
  snd = ssn.sender(addr)

  count = 0
  start = time.time()
  while (opts.count == 0 or count < opts.count) and \
        (opts.timeout is None or time.time() - start < opts.timeout):
    msg = Message(subject=opts.subject,
                  reply_to=opts.reply_to,
                  content=content)
    msg.properties["spout-id"] = "%s:%s" % (spout_id, count)
    for p in opts.properties:
      name, val = nameval(p)
      msg.properties[name] = val

    snd.send(msg)
    count += 1
    print msg
except SendError, e:
  print e
except KeyboardInterrupt:
  pass

conn.close()