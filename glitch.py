#import matplotlib.pyplot as plt # type: ignore

# GlitchController will be part of ChipWhisperer core - just run this block
# for now.

try:
    import ipywidgets as widgets # type: ignore
except ModuleNotFoundError:
    widgets = None

class GlitchController:
    
    def __init__(self, groups, parameters):
        self.groups = groups
        self.parameters = parameters
        
        self.results = GlitchResults(groups=groups, parameters=parameters)
        
        self.parameter_min = [0.0] * len(parameters)
        self.parameter_max = [10.0] * len(parameters)
        self.steps = [[1]] * len(parameters) # add a separate step setting for each parameter
        
        self.widget_list_parameter = None
        self.widget_list_groups = None

        self._dmaps = None
        self._buffers = None
        self._glitch_plotdots = None
        
        self.clear()
        
    def clear(self):
        self.results.clear()        
        self.group_counts = [0] * len(self.groups)
        
        if self.widget_list_groups:
            for w in self.widget_list_groups:
                w.value = 0
        
    def set_range(self, parameter, low, high):
        
        if high < low:
            t = low
            low = high
            high = t
        
        i = self.parameters.index(parameter)
        self.parameter_min[i] = low
        self.parameter_max[i] = high
        if not (widgets is None): 
            if self.widget_list_parameter:
                # When changing them, need to ensure we don't have min > max ever or will throw
                # an error, so we set max to super-high first.
                self.widget_list_parameter[i].max = 1E9
                self.widget_list_parameter[i].min = low
                self.widget_list_parameter[i].max = high
    
    def set_step(self, parameter, step):
        '''Set a step for a single parameter

        Can be a single value, or a list of step-sizes.

        Single values will be extended to match the length of the rest of 
        parameters' step-sizes.

        Lists must match the length of other step sizes.

        Example::

            gc.set_global_step([1, 2, 3])
            gc.set_step("width", 10) # eqv to [10, 10, 10]
            gc.set_step("offset", [5, 10, 15])
            gc.set_step("ext_offset", [1, 2]) # error, list too short
            gc.set_step(2, [1, 2, 5, 10]) # error, list too long
        '''
        if type(parameter) is str:
            parameter = self.parameters.index(parameter)
        if hasattr(step, "__iter__"):
            if len(step) != self._num_steps:
                raise ValueError("Invalid number of steps {}")
            self.steps[parameter] = step
        else:
            self.steps[parameter] = [step] * self._num_steps



        
    def set_global_step(self, steps):
        '''Set step for all parameters. 
        
        Can be a single value, or a list of step-sizes to iterate through.

        Single values will be converted to a list of length 1.
        
        Overwrites individually set steps.
        '''
        for i in range(len(self.steps)):
            if hasattr(steps, "__iter__"):
                self.steps[i] = steps
            else:
                self.steps[i] = [steps]
        self._num_steps = len(self.steps[0])

    
    def add(self, group, parameters=None, strdesc=None, metadata=None, plot=True):
        if parameters is None:
            parameters = self.parameter_values
        self.results.add(group, parameters, strdesc, metadata)    
        
        i = self.groups.index(group)        
        #Basic count
        self.group_counts[i] += 1
        # self.widget_list_groups[i].value =  self.group_counts[i] # modify bug in script .py

        if plot and self._buffers:
            self.update_plot(parameters[self._x_index], parameters[self._y_index], group)

    def glitch_plot(self, plotdots, x_index=0, y_index=1, x_bound=None, y_bound=None, bufferlen=10000):
        import holoviews as hv # type: ignore
        from holoviews.streams import Buffer # type: ignore
        from pandas import DataFrame # type: ignore
        hv.extension('bokeh', logo=False) #don't display logo, otherwise it pops up everytime this func is called.
        if type(x_index) is str:
            x_index = self.parameters.index(x_index)
        if type(y_index) is str:
            y_index = self.parameters.index(y_index)

        self._glitch_plotdots = plotdots
        self._buffers = {}
        self._dmaps = {}
        self._x_index = x_index
        self._y_index = y_index

        x_label = self.parameters[x_index]
        y_label = self.parameters[y_index]

        for k in plotdots.keys():
            if plotdots[k] is None:
                continue
            self._buffers[k] = Buffer(DataFrame({'x': [], 'y': []}, columns=['x', 'y']), length=bufferlen, index=False)
            self._dmaps[k] = hv.DynamicMap(hv.Points, streams=[self._buffers[k]]).opts(height=600, width=800, 
                framewise=True, size=10, marker=plotdots[k][0], color=plotdots[k][1], tools=['hover'])


        plot_iter = iter(self._dmaps)
        plot = self._dmaps[next(plot_iter)]

        for tmp in plot_iter:
            plot *= self._dmaps[tmp]

        if not x_bound:
            x_bound = {}
        else:
            x_bound = {"range": x_bound}

        if not y_bound:
            y_bound = {}
        else:
            y_bound = {"range": y_bound}
        return plot.redim(x=hv.Dimension(x_label, **x_bound), y=hv.Dimension(y_label, **y_bound))
        
    def update_plot(self, x, y, label):
        from pandas import DataFrame # type: ignore
        if label not in self._buffers:
            #raise ValueError("Invalid label {}. Valid labels are {}".format(label, self._buffers.keys()))
            return #probably a label not used
        self._buffers[label].send(DataFrame([(x, y)], columns=['x', 'y']))
    
    def display_stats(self):
        if widgets is None:
            raise ModuleNotFoundError("Could not load ipywidgets, display not available")
        self.widget_list_groups = [widgets.IntText(value=0, description=group + " count:", disabled=True)
                                   for group in self.groups]
        
        self.widget_list_parameter = [widgets.FloatSlider(
                                            value=self.parameter_min[i],
                                            min=self.parameter_min[i],
                                            max=self.parameter_max[i],
                                            step=0.01,
                                            description=p + " setting:",
                                            disabled=True,
                                            continuous_update=False,
                                            orientation='horizontal',
                                            readout=True,
                                            readout_format='.01f')
                                          for i,p in enumerate(self.parameters)]
            
        display(*(self.widget_list_groups + self.widget_list_parameter))

    def plot_2d(self, plotdots=None, x_index=0, y_index=1, *args, **kwargs):
        if type(x_index) is str:
            x_index = self.parameters.index(x_index)
        if type(y_index) is str:
            y_index = self.parameters.index(y_index)
        if plotdots is None:
            plotdots = self._glitch_plotdots

        return self.results.plot_2d(plotdots, x_index, y_index, *args, **kwargs)

       
        
    def glitch_values(self, clear=True):
        """Generator returning the given parameter values in order, using the step size (or step list)"""
        
        self.parameter_values = self.parameter_min[:]
        
        if clear:
            self.clear()
        
        #transpose steps so that all parameters' steps get passed to loop_rec instead of just one
        steps = list(map(list, zip(*self.steps)))

        for stepsize in steps:
            for val in self._loop_rec(0, len(self.parameter_values)-1, stepsize):
                if self.widget_list_parameter:
                    for i,v in enumerate(val):
                        self.widget_list_parameter[i].value = v
                yield val

        
        
    def _loop_rec(self, parameter_index, final_index, step):
        self.parameter_values[parameter_index] = self.parameter_min[parameter_index]
        if parameter_index == final_index:            
            while self.parameter_values[parameter_index] <= self.parameter_max[parameter_index]:                                
                yield self.parameter_values
                self.parameter_values[parameter_index] += step[parameter_index]
        else:
            while self.parameter_values[parameter_index] <= self.parameter_max[parameter_index]: 
                yield from self._loop_rec(parameter_index+1, final_index, step)
                self.parameter_values[parameter_index] += step[parameter_index]

    def calc(self, ignore_params=[], sort=None):
        if (type(ignore_params) is int) or (type(ignore_params) is str):
            ignore_params = [ignore_params]

        new_param_list = []
        for param in ignore_params:
            if type(param) is str:
                new_param_list.append(self.parameters.index(param))
            else:
                new_param_list.append(param)

        rtn = self.results.calc(ignore_params=new_param_list)
        if sort:
            rtn = sorted(rtn.items(), key=lambda x: x[1][sort])
            rtn.reverse()
        else:
            rtn =list(rtn.items())
        return rtn
                

class GlitchResults:
    """GlitchResults tracks and plots fault injection attempts.
    
    When creating a new object, you must specify the groups of potential glitch
    results (such as 'success' or 'reset'), along with what parameters will be
    varied during this experimentation. For example a typical clock glitching
    setup might look like::
    
        gr = GlitchResults(groups=["success", "reset", "normal"], 
                           parameters=["width", "offset"])
        
    The order the groups ("success", etc) takes is used as a priority when later
    plotting results. The first group (in this case "success" in that list) that
    shows *any* results will become the reported effect of that fault. This is
    done as typically you'd prefer to spot say a 5% success rate than a 95% reset
    or normal rate. Once the object is initialized as above, we could add some
    data to it::
    
        gr.add("reset", (12.3, 33.4))
        gr.add("success", (12.4, 33.8))
        gr.add("reset", (12.4, 33.8))
    
    While this simple example is manually added data, it should be normally added
    by viewing the results of a glitch. You could now visualize this with a graph::
    
        gr.plot_2d(plotdots={"success":"og", "reset":"xr", "normal":".k"})
    
    Note before importing if using Jupyter, you may want to use the notebook magic::
    
        %matplotlib notebook
    
    """
    
    def __init__(self, groups, parameters):
        self.groups = groups
        self.parameters = parameters
        self._result_dict = {}
        
    def clear(self):
        '''
        Clears stored statistics in preperation for a new run.
        '''
        self._result_dict = {}

    def results(self, ignore_params=[]):
        """Returns results as a dictionary of 
        results = {
            (param1, param2, ...): (num_total, num_group1, num_group2, ...)
        }
            {'params': (params), 'groups': n_A1, 'groupB': n_B1, "groupC": n_C1, ...},
            {'param1': p_12, 'param2': p_22, ..., 'groupA': n_A2, 'groupB': n_B2, "groupC": n_C2, ...},
        ]

        Where p_1x, p_2x, ... is a unique grouping of parameters (i.e. width = 10, offset = 20, ...)
        and n_A1
        """
        return None
        
    def add(self, group, parameters, strdesc=None, metadata=None):
        '''
        Add a result to ChipWhisperer glitch map generator.
        '''
        if group not in self.groups:
            raise ValueError("Invalid group {} (groups are {})".format(group, self.groups))
        if len(parameters) != len(self.parameters):
            raise ValueError("Invalid number of parameters passed: {:d} passed, {:d} expected".format(len(parameters), len(self.parameters)))

        parameters = tuple(parameters) # make sure parameters is a tuple so it can be hashed

        # if the parameters aren't already in the dict, add an entry for them
        if not parameters in self._result_dict: 
            self._result_dict[parameters] = {'total': 0}
            for k in self.groups:
                self._result_dict[parameters][k] = 0
                self._result_dict[parameters][k+'_rate'] = 0 # entry for success/reset/etc rate, makes plotting easier

        # add to the group totals
        self._result_dict[parameters][group] += 1
        self._result_dict[parameters]['total'] += 1

    def res_dict_of_lists(self, results):
        rtn = {}

        # create a list of values for each parameter
        orig_key = next(iter(results))
        for i in range(len(orig_key)):
            rtn[self.parameters[i]] = [p[i] for p in results]

        # do the same for each group/group success rate

        orig_val = next(iter(results.values())) # grab group dict for first parameter

        for k in orig_val:
            rtn[k] = [results[p][k] for p in results] # add a list for each group success rate

        return rtn


        
    def calc(self, ignore_params=[]):
        '''
        Calculate how many glitches had various effects. Return updated stats.

        Can ignore parameters, combining their results. For example, with 3 parameters,
        ignoring parmameter 2 will combine the results where parameter 0 and 1 are the same,
        but 2 is different.
        '''

        # make sure ignore_params is a list
        if type(ignore_params) is int:
            ignore_params = [ignore_params]

        ignore_params = list(ignore_params)
        ignore_params.sort()
        ignore_params.reverse()

        rtn = {}

        # combine results, ignoring ignore_param
        for param in self._result_dict:

            # param tuple needs to be list so we can delete entries
            new_param = list(param)

            # delete params that we're ignoring
            for p in ignore_params:
                del(new_param[p])

            # now needs to be tuple so can use as index for dict
            new_param = tuple(new_param)

            # combine groups
            if new_param in rtn:
                # already have these settings, so add in new totals
                for group in rtn[new_param]:
                    # print("adding group " + str(group))
                    rtn[new_param][group] += self._result_dict[param][group]
                # rtn[new_param]['total'] += self._result_dict[param]['total']
            else:
                rtn[new_param] = dict(self._result_dict[param])
        
        # calculate rate of occurrence for each group
        for param in rtn:
            for group in self.groups:
                rtn[param][group+'_rate'] = rtn[param][group] / rtn[param]['total']
        
        return rtn

    def plot_2d(self, plotdots, x_index=0, y_index=1, x_units=None, y_units=None, alpha=True):
        '''
        Generate a 2D plot of glitch success rate using matplotlib.

        Plotting is done in the default figure - you may need to call plt.figure() before and
        plt.show() after calling this function if you want more control (or the figure does
        not show by default).
        '''
        import holoviews as hv # type: ignore
        from holoviews import opts # type: ignore
        hv.extension('bokeh', logo=False) #don't display logo, otherwise it pops up everytime this func is called.
        plot = hv.Points([])
        if type(x_index) is str:
            x_index = self.parameters.index(x_index)
        if type(y_index) is str:
            y_index = self.parameters.index(y_index)

        # remove parameters from data that we won't be plotting
        remove_params = list(range(len(self.parameters)))
        if x_index > y_index:
            del(remove_params[x_index])
            del(remove_params[y_index])
        else:
            del(remove_params[y_index])
            del(remove_params[x_index])

        data = self.calc(remove_params)

        # get data as {'param0': [list], 'param1': [list], 'group0_rate': n, ...} for easy plotting
        fmt_data = self.res_dict_of_lists(data)


        #We only want legend to show for first element... bit of a hack here
        legs = self.groups[:]
        # remove datapoints with zero % group rate
        def remove_zeros(result, group):
            rtn = {}
            for key in result:
                rtn[key] = [result[key][i] for i, j in enumerate(result[key]) if result[group][i] > 0]
            return rtn
        

        # Plot once for each group
        for g in self.groups:
            if plotdots[g]:
                # plot everything, but if group rate is 0, it'll be fully transparent
                # if g in legs:
                group_data = remove_zeros(fmt_data, g)

                leg = {'label': g.title()}
                    #No need to show this one anymore

                #     legs.remove(g)
                # else:
                #     leg = {}

                if len(plotdots[g]) < 2:
                    raise ValueError("Invalid plotdot {}, must be 2 chars long".format(plotdots[g]))
                if alpha:
                    plot *= hv.Points(group_data, **leg, kdims=[self.parameters[x_index], self.parameters[y_index]],
                        vdims=[g+'_rate']).opts(\
                        color=plotdots[g][1], marker=plotdots[g][0], size=10, height=600, width=800, alpha=g+'_rate', tools=['hover'])
                else:
                    plot *= hv.Points(group_data, **leg, kdims=[self.parameters[x_index], self.parameters[y_index]], vdims=[g+'_rate']).opts(\
                            color=plotdots[g][1], marker=plotdots[g][0], size=10, height=600, width=800, tools=['hover'])

        xlabel = self.parameters[x_index].title()
        if x_units:
            xlabel += " (" + x_units + ")"
        # plt.xlabel(xlabel)

        ylabel = self.parameters[y_index].title()
        if y_units:
            ylabel += " (" + y_units + ")"
        # plt.ylabel(ylabel)

        plot.redim(y=hv.Dimension(ylabel), x=hv.Dimension(xlabel))

        return plot