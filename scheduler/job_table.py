from job_template import JobTemplate

def resnet18(batch_size, privacy_consume):
    model = 'ResNet-18 (batch size %d)' % (batch_size)
    command = 'python3 main.py --data_dir=%s/cifar10'
    command += ' --batch_size %d' % (batch_size)
    working_directory = 'image_classification/cifar10'
    num_steps_arg = '--num_steps'
    mem_request = float(batch_size / 8)
    target_dataset = 'dataset0'
    return JobTemplate(model=model, command=command, working_directory=working_directory,
                       num_steps_arg=num_steps_arg, mem_request=mem_request, 
                       privacy_consume=privacy_consume, target_dataset=target_dataset, distributed=True)

def resnet50(batch_size, privacy_consume):
    model = 'ResNet-50 (batch size %d)' % (batch_size)
    command = 'python3 main.py -j 8 -a resnet50 -b %d' % (batch_size)
    command += ' %s/imagenet/'
    working_directory = 'image_classification/imagenet'
    num_steps_arg = '--num_minibatches'
    mem_request = float(batch_size / 4)
    target_dataset = 'dataset0'
    return JobTemplate(model=model, command=command,
                       working_directory=working_directory, num_steps_arg=num_steps_arg, 
                       mem_request=mem_request, privacy_consume=privacy_consume, 
                       target_dataset=target_dataset, distributed=True)

def transformer(batch_size, privacy_consume):
    model = 'Transformer (batch size %d)' % (batch_size)
    command = 'python3 train.py -data %s/translation/multi30k.atok.low.pt'
    command += ' -batch_size %d -proj_share_weight' % (batch_size)
    working_directory = 'translation'
    num_steps_arg = '-step'
    mem_request = float(batch_size / 8)
    target_dataset = 'dataset0'
    return JobTemplate(model=model, command=command,
                       working_directory=working_directory,
                       num_steps_arg=num_steps_arg, mem_request=mem_request, 
                       privacy_consume=privacy_consume, target_dataset=target_dataset, distributed=True)

def lm(batch_size, privacy_consume):
    model = 'LM (batch size %d)' % (batch_size)
    command = 'python main.py --cuda --data %s/wikitext2'
    command += ' --batch_size %d' % (batch_size)
    working_directory = 'language_modeling'
    num_steps_arg = '--steps'
    mem_request = float(batch_size / 5)
    target_dataset = 'dataset0'
    return JobTemplate(model=model, command=command,
                       working_directory=working_directory,
                       num_steps_arg=num_steps_arg, mem_request=mem_request, 
                       privacy_consume=privacy_consume, target_dataset=target_dataset, distributed=True)

def recommendation(batch_size, privacy_consume):
    model = 'Recommendation (batch size %d)' % (batch_size)
    command = 'python3 train.py --data_dir %s/ml-20m/pro_sg/'
    command += ' --batch_size %d' % (batch_size)
    working_directory = 'recommendation'
    num_steps_arg = '-n'
    mem_request = float(batch_size / 256)
    target_dataset = 'dataset0'
    return JobTemplate(model=model, command=command,
                       working_directory=working_directory,
                       num_steps_arg=num_steps_arg, mem_request=mem_request,
                       privacy_consume=privacy_consume, target_dataset=target_dataset)

def a3c(privacy_consume):
    model = 'A3C'
    command = ('python3 main.py --env PongDeterministic-v4 --workers 4 '
               '--amsgrad True')
    working_directory = 'rl'
    num_steps_arg = '--max-steps'
    mem_request = 16.0
    target_dataset = 'dataset0'
    return JobTemplate(model=model, command=command,
                       working_directory=working_directory,
                       num_steps_arg=num_steps_arg, mem_request=mem_request, 
                       privacy_consume=privacy_consume, target_dataset=target_dataset, 
                       needs_data_dir=False)

def cyclegan(privacy_consume):
    model = 'CycleGAN'
    working_directory = 'cyclegan'
    command = ('python3 cyclegan.py --dataset_path %s/monet2photo'
               ' --decay_epoch 0')
    num_steps_arg = '--n_steps'
    mem_request = 16.0
    target_dataset = 'dataset0'
    return JobTemplate(model=model, command=command,
                       working_directory=working_directory,
                       num_steps_arg=num_steps_arg, 
                       mem_request=mem_request, privacy_consume=privacy_consume,
                       target_dataset=target_dataset)

JobTable = []
all_privacy_used_config = [float(1 / 10)]

for privacy_consume in all_privacy_used_config:
    for batch_size in [16, 32, 64, 128, 256]:
        JobTable.append(resnet18(batch_size, privacy_consume))
    for batch_size in [16, 32, 64, 128]:
        JobTable.append(resnet50(batch_size, privacy_consume))
    for batch_size in [16, 32, 64, 128, 256]:
        JobTable.append(transformer(batch_size, privacy_consume))
    for batch_size in [5, 10, 20, 40, 80]:
        JobTable.append(lm(batch_size, privacy_consume))
    for batch_size in [512, 1024, 2048, 4096, 8192]:
        JobTable.append(recommendation(batch_size, privacy_consume))
    JobTable.append(a3c(privacy_consume))
    JobTable.append(cyclegan(privacy_consume))
