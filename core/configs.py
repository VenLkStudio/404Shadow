# config1 = '-q1+s -s25+s -o5+s -f-1'
# config1_l = ['ciadpiwin', '-q1+s', '-s25+s', '-o5+s', '-f-1', '-S']
# config2 = '-q1+s -s29+s -o5+s -f-1'
# config3 = '-Ku -a1 -An -Kt,h -d7 -s2 -An'
# config4 = '-s1 -q1 -Y -At -f-1 -r1+s -As'
# config5 = '-q1+s -s25+s -o5+s -f-1 -S -As'
# config6 = '-q1+s -s29+s -o5+s -f-1 -S -As'
# config7 = '-Ku -a1 -An -Kt,h -q1 -r25+s -An'
# config8 = '-n vk.com -q 1+s -O 1 -s 25+s -t 5'

def get_count():
    with open('bin/lists/hosts.txt') as f:
        count = sum(1 for line in f)
        return count
    
def get_config(id):
    # f = open('bin/lists/hosts.txt')
    with open('bin/proxy_cmds.txt') as f:
        for line, arg in enumerate(f):
            if line == id-1:
                return arg
                # print(i)
